"""Permission contracts supplied by the team; never infer permissions from a role name."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect

from pages.loginPage import LoginPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('role', ['ADMIN', 'ANALYST', 'MLRO', 'COMPLIANCE_OFFICER', 'CLIENT'])
def test_role_ui_and_api_permissions_match_approved_matrix(browser, base_url, review_origin, role):
    matrix_path = os.getenv('WORKFLOW_PERMISSION_MATRIX', '').strip()
    if not matrix_path:
        pytest.skip('Set WORKFLOW_PERMISSION_MATRIX to the approved role policy JSON file.')
    matrix = json.loads(Path(matrix_path).read_text(encoding='utf-8'))
    checks = matrix.get(role)
    assert checks and checks.get('pages') and checks.get('api'), f'{role} needs explicit page and API expectations.'
    email = os.getenv(f'WORKFLOW_{role}_EMAIL')
    password = os.getenv(f'WORKFLOW_{role}_PASSWORD')
    if not email or not password:
        pytest.skip(f'Set WORKFLOW_{role}_EMAIL and WORKFLOW_{role}_PASSWORD for a disposable role account.')

    context = browser.new_context()
    blocked = []
    try:
        page = context.new_page()
        login = LoginPage(page)
        login.open(base_url)
        login.login(email, password)
        expect(page.get_by_role('heading', name='Welcome', exact=True)).to_be_visible(timeout=30000)

        def readonly(route):
            if route.request.method in ('GET', 'HEAD', 'OPTIONS'):
                route.continue_()
            else:
                blocked.append(urlsplit(route.request.url).path)
                route.abort()

        context.route('**/api/**', readonly)
        for check in checks['pages']:
            path = check['path']
            assert path.startswith('/nolimit/app/'), 'Permission checks must target an application route.'
            page.goto(review_origin + path, wait_until='domcontentloaded')
            if check['allowed']:
                expect(page.get_by_role('heading', name=check['heading'], exact=True)).to_be_visible(timeout=20000)
            else:
                # Assert actual denial feedback, rather than merely a missing button.
                expect(page.get_by_text(check['denial_text'], exact=True)).to_be_visible(timeout=20000)
                expect(page.get_by_role('heading', name=check['heading'], exact=True)).to_have_count(0)

        raw_token = page.evaluate("localStorage.getItem('accessToken:nolimit')")
        assert raw_token, 'The role account lost its session during navigation.'
        try:
            token = json.loads(raw_token)
        except json.JSONDecodeError:
            token = raw_token
        assert isinstance(token, str), 'Unexpected access token storage format.'
        for check in checks['api']:
            endpoint = check['url']
            parsed = urlsplit(endpoint)
            assert parsed.scheme == 'https' and parsed.hostname == 'sentinel-austrac-qa-be.northlark.com'
            assert parsed.path.startswith('/api/v1/') and check['status'] in (200, 403)
            # Only exact, approved GET endpoints; never enumerate another client's IDs.
            response = context.request.get(endpoint, headers={'Authorization': 'Bearer ' + token}, max_redirects=0)
            assert response.status == check['status'], f'{role}: unexpected status for {parsed.path}'
            assert 'application/json' in response.headers.get('content-type', '')
        assert not blocked, f'The permission checks attempted a write: {blocked}'
    finally:
        context.close()
