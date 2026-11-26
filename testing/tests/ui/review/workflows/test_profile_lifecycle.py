"""Password/signature persistence on a dedicated disposable account, with restoration."""
import hashlib
import os
import secrets

import pytest
from playwright.sync_api import expect

from pages.loginPage import LoginPage
from pages.reviewRequests import QA_API, session_headers
from pages.settingsPage import SettingsPage
from pages.uploadSamples import png_bytes


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write]


@pytest.fixture
def profile_account(request, browser_name, base_url, review_origin):
    if os.getenv('WORKFLOW_ALLOW_WRITES') != '1' or os.getenv('WORKFLOW_PROFILE_ACCOUNT') != '1':
        pytest.skip('Enable WORKFLOW_ALLOW_WRITES=1 and WORKFLOW_PROFILE_ACCOUNT=1 for a disposable account.')
    assert os.getenv('WORKFLOW_DISPOSABLE_DATA_CONFIRMED') == '1'
    assert not os.getenv('PYTEST_XDIST_WORKER'), 'Run account mutations with -n 0.'
    email = os.getenv('WORKFLOW_PROFILE_EMAIL', '').strip()
    password = os.getenv('WORKFLOW_PROFILE_PASSWORD')
    assert email and password and email.casefold() != os.getenv('TEST_EMAIL', '').casefold(), 'Provide a dedicated WORKFLOW_PROFILE_EMAIL/PASSWORD, different from TEST_EMAIL.'
    browser = request.getfixturevalue('browser')
    contexts = []

    def login(secret=password):
        context = browser.new_context()
        contexts.append(context)
        page = context.new_page()
        form = LoginPage(page)
        form.open(base_url)
        form.login(email, secret)
        expect(page).to_have_url(review_origin + '/nolimit/app/home', timeout=30000)
        return page

    try:
        yield login, email, password, review_origin
    finally:
        for context in contexts:
            context.close()


def change_password(page, origin, old, new):
    settings = SettingsPage(page, origin)
    settings.open('Profile Settings')
    settings.main.get_by_placeholder('Enter old password', exact=True).fill(old)
    settings.main.get_by_placeholder('Enter new password', exact=True).fill(new)
    settings.main.get_by_placeholder('Enter confirm password', exact=True).fill(new)
    with page.expect_response(lambda response: '/auth/change-password' in response.url and response.request.method == 'PUT') as pending:
        settings.main.get_by_role('button', name='Change Password', exact=True).click()
    return pending.value


@pytest.mark.negative
def test_negative_wrong_current_password_cannot_change_account(profile_account):
    login, _, original, origin = profile_account
    page = login()
    response = change_password(page, origin, 'Wrong-QA-' + secrets.token_hex(12), 'Aa1!' + secrets.token_urlsafe(24))
    assert response.status in (400, 401, 403, 422), 'Wrong current password was accepted.'
    # A fresh real login confirms that the original credential is still valid.
    login(original)


@pytest.mark.parametrize('case', ['new-login-and-old-rejection', 'other-session-revocation'])
def test_positive_password_change_and_restore(profile_account, request, case):
    login, email, original, origin = profile_account
    policy = {}
    if case == 'other-session-revocation':
        policy = request.getfixturevalue('agreed_rules').get('session', {})
        for key in ('password_change_revokes_other_access', 'password_change_revokes_other_refresh'):
            if policy.get(key) is None:
                pytest.skip(f'Confirm session.{key} in WORKFLOW_RULES_FILE.')
            assert isinstance(policy[key], bool)
    page = login()
    other = login() if case == 'other-session-revocation' else None
    other_headers = session_headers(other) if other else None
    refresh = None
    if other:
        import json
        raw = other.evaluate("localStorage.getItem('refreshToken:nolimit')")
        assert raw
        try:
            refresh = json.loads(raw)
        except json.JSONDecodeError:
            refresh = raw
    generated = 'Aa1!' + secrets.token_urlsafe(24)
    changed = False
    try:
        response = change_password(page, origin, original, generated)
        assert 200 <= response.status < 300 and response.json().get('success') is not False
        changed = True
        fresh = login(generated)
        if other:
            result = other.context.request.get(QA_API + '/auth/me', headers=other_headers)
            assert result.status in ((401, 403) if policy['password_change_revokes_other_access'] else (200,))
            result = other.context.request.post(QA_API + '/auth/refresh-token', headers={'x-tenant-slug': 'nolimit'}, data={'token': refresh})
            assert result.status in ((401, 403) if policy['password_change_revokes_other_refresh'] else (200,))
        else:
            # Only one failed login, against this dedicated account, after verifying the new one.
            rejected = fresh.context.request.post(QA_API + '/auth/login', headers={'x-tenant-slug': 'nolimit'},
                                                  data={'email': email, 'password': original})
            assert rejected.status in (400, 401, 403, 422), 'The old password still authenticates.'
    finally:
        if changed:
            restore_page = login(generated)
            restored = change_password(restore_page, origin, generated, original)
            assert 200 <= restored.status < 300 and restored.json().get('success') is not False, 'Restore the dedicated account password before reuse.'
            login(original)


@pytest.mark.positive
def test_positive_signature_upload_survives_reload_and_is_restored(profile_account):
    login, _, _, origin = profile_account
    page = login()
    headers = session_headers(page)
    identity = page.context.request.get(QA_API + '/auth/me', headers=headers)
    assert identity.status == 200
    data = identity.json()['data']
    user = data.get('user', data)
    identifier = user.get('refId')
    assert identifier
    previous = user.get('signature')
    if not previous or not previous.get('fileKey'):
        pytest.skip('Provide a disposable profile account with an existing restorable PNG/JPEG signature.')
    assert previous.get('fileType', '').lower() in ('png', 'jpg', 'jpeg')
    saved = page.context.request.get(QA_API + '/documents/download-file', params={'fileKey': previous['fileKey']}, headers=headers)
    assert saved.status == 200
    file_data = saved.json().get('data', saved.json()).get('fileData')
    import base64
    assert isinstance(file_data, str), 'The signature download must provide base64 fileData for restoration.'
    old_bytes = base64.b64decode(file_data.split(',', 1)[-1], validate=True)
    endpoint = QA_API + '/user-management/signature/' + identifier
    changed = False
    try:
        settings = SettingsPage(page, origin)
        settings.open('Profile Settings')
        settings.main.locator('.signature-uploader .edit-sign').click()
        modal = settings.modal
        modal.get_by_text('UPLOAD', exact=True).click()
        modal.locator('input[type="file"]').set_input_files({'name': 'qa-signature.png', 'mimeType': 'image/png', 'buffer': png_bytes()})
        with page.expect_response(lambda response: response.url == endpoint and response.request.method == 'PUT') as pending:
            modal.get_by_role('button', name='Add Signature', exact=True).click()
        assert 200 <= pending.value.status < 300
        changed = True
        expect(modal).to_have_count(0)
        page.reload(wait_until='domcontentloaded')
        image = settings.main.locator('.signature-preview img.signature-image')
        expect(image).to_be_visible(timeout=20000)
        assert image.evaluate('(element) => element.complete && element.naturalWidth > 0'), 'Saved signature did not render.'
        current = page.context.request.get(QA_API + '/auth/me', headers=headers).json()['data']
        current = current.get('user', current)
        assert current['signature']['fileKey'] != previous['fileKey'], 'Reload still shows the original signature record.'
    finally:
        if changed:
            restored = page.context.request.put(endpoint, headers=headers, multipart={
                'file': {'name': 'restored-signature.' + previous['fileType'], 'mimeType': 'image/' + previous['fileType'], 'buffer': old_bytes},
            })
            assert 200 <= restored.status < 300, 'Restore the dedicated account signature before reuse.'
            result = page.context.request.get(QA_API + '/auth/me', headers=headers).json()['data']
            result = result.get('user', result)
            restored_file = page.context.request.get(QA_API + '/documents/download-file', params={'fileKey': result['signature']['fileKey']}, headers=headers)
            assert restored_file.status == 200
            payload = restored_file.json().get('data', restored_file.json())['fileData']
            assert hashlib.sha256(base64.b64decode(payload.split(',', 1)[-1])).digest() == hashlib.sha256(old_bytes).digest()
