"""Direct backend authentication checks; no invalid password attempts or ID enumeration."""
import pytest

from pages.reviewRequests import QA_API


pytestmark = [pytest.mark.ui, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('endpoint', [
    'auth/me', 'auth/profile', 'clients', 'transactions',
    'notifications', 'user-management',
])
@pytest.mark.parametrize('token', ['', 'not-a-jwt', 'eyJhbGciOiJub25lIn0.eyJzdWIiOiJxYS10ZXN0IiwiZXhwIjoxfQ.'],
                         ids=['missing-token', 'malformed-token', 'forged-expired-token'])
def test_negative_protected_api_rejects_invalid_authentication(guest_page, endpoint, token):
    headers = {'x-tenant-slug': 'nolimit'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    response = guest_page.context.request.get(QA_API + '/' + endpoint, headers=headers, max_redirects=0)
    assert response.status in (401, 403), f'{endpoint} accepted missing/invalid authentication: HTTP {response.status}'
    assert 'application/json' in response.headers.get('content-type', '')
    body = response.json()
    assert not body.get('data'), f'{endpoint} exposed a data payload on an authentication error.'
    assert 'accessToken' not in body and 'refreshToken' not in body


@pytest.mark.parametrize('token', ['', 'not-a-jwt'])
def test_negative_configuration_does_not_expose_settings_to_anonymous_requests(guest_page, token):
    headers = {'x-tenant-slug': 'nolimit'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    response = guest_page.context.request.get(QA_API + '/config', headers=headers, max_redirects=0)
    # Observed anonymous behaviour is an HTTP 200 envelope with no settings.
    # Authentication failures are also safe; no requirement for a specific error code is invented.
    assert response.status in (200, 401, 403)
    assert not response.json().get('data'), 'Anonymous config request exposed tenant settings.'
