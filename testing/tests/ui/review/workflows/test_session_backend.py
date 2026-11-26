"""Real refresh/logout behaviour on a dedicated account, separate from the supplied admin."""
import json
import os
import base64
import time

import pytest
from playwright.sync_api import expect

from pages.loginPage import LoginPage
from pages.reviewRequests import QA_API, session_headers


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write]


@pytest.fixture
def disposable_session(request, browser_name, base_url):
    if os.getenv('WORKFLOW_SESSION_SECURITY') != '1':
        pytest.skip('Set WORKFLOW_SESSION_SECURITY=1 and provide a dedicated session-test account.')
    email = os.getenv('WORKFLOW_SESSION_EMAIL')
    password = os.getenv('WORKFLOW_SESSION_PASSWORD')
    assert email and password and email != os.getenv('TEST_EMAIL'), 'Use a separate disposable account for logout/revocation checks.'
    browser = request.getfixturevalue('browser')
    context = browser.new_context()
    try:
        page = context.new_page()
        login = LoginPage(page)
        login.open(base_url)
        login.login(email, password)
        expect(page.get_by_role('heading', name='Welcome', exact=True)).to_be_visible(timeout=30000)
        headers = session_headers(page)
        raw = page.evaluate("localStorage.getItem('refreshToken:nolimit')")
        assert raw, 'Login did not provision a refresh token.'
        try:
            refresh = json.loads(raw)
        except json.JSONDecodeError:
            refresh = raw
        assert isinstance(refresh, str)
        yield context.request, headers, refresh
    finally:
        if 'headers' in locals():
            context.request.post(QA_API + '/auth/logout', headers=headers)
        context.close()


@pytest.mark.positive
def test_positive_real_refresh_produces_usable_access_token(disposable_session):
    request, headers, refresh = disposable_session
    response = request.post(QA_API + '/auth/refresh-token', headers={'x-tenant-slug': 'nolimit'}, data={'token': refresh})
    assert response.status == 200
    token = response.json().get('data', {}).get('accessToken')
    assert isinstance(token, str) and token
    result = request.get(QA_API + '/auth/me', headers={**headers, 'Authorization': 'Bearer ' + token})
    assert result.status == 200


@pytest.mark.negative
def test_negative_logout_revokes_refresh_token(disposable_session):
    request, headers, refresh = disposable_session
    assert request.post(QA_API + '/auth/logout', headers=headers).status in (200, 204)
    response = request.post(QA_API + '/auth/refresh-token', headers={'x-tenant-slug': 'nolimit'}, data={'token': refresh})
    assert response.status in (401, 403)
    assert not (response.json().get('data') or {}).get('accessToken')


@pytest.mark.negative
def test_negative_post_logout_access_obeys_agreed_revocation_policy(disposable_session, agreed_rules):
    request, headers, _ = disposable_session
    revokes = agreed_rules.get('session', {}).get('logout_revokes_access')
    if revokes is None:
        pytest.skip('Confirm session.logout_revokes_access in WORKFLOW_RULES_FILE.')
    assert isinstance(revokes, bool)
    assert request.post(QA_API + '/auth/logout', headers=headers).status in (200, 204)
    response = request.get(QA_API + '/auth/me', headers=headers)
    assert response.status in ((401, 403) if revokes else (200,))


@pytest.mark.negative
def test_negative_real_issued_access_token_expires(disposable_session, agreed_rules):
    request, headers, _ = disposable_session
    leeway = agreed_rules.get('session', {}).get('access_expiry_leeway_seconds')
    if leeway is None:
        pytest.skip('Confirm the server access-token expiry leeway in WORKFLOW_RULES_FILE.')
    assert isinstance(leeway, int) and leeway >= 0
    token = headers['Authorization'].split(' ', 1)[1]
    segment = token.split('.')[1]
    claims = json.loads(base64.urlsafe_b64decode(segment + '=' * (-len(segment) % 4)))
    assert isinstance(claims.get('exp'), (int, float)), 'The issued token has no expiry claim.'
    remaining = max(0, claims['exp'] + leeway + 1 - time.time())
    budget = int(os.getenv('WORKFLOW_SESSION_EXPIRY_WAIT_SECONDS', '0'))
    if remaining > budget:
        pytest.skip('The real token expiry exceeds WORKFLOW_SESSION_EXPIRY_WAIT_SECONDS; no server clock is forged.')
    time.sleep(remaining)
    response = request.get(QA_API + '/auth/me', headers=headers)
    assert response.status in (401, 403), 'A legitimately issued expired access token still grants access.'
