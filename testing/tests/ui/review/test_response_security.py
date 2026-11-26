"""Read-only HTTP security regressions against the approved QA origins."""
import pytest

from pages.reviewRequests import QA_API, session_headers


pytestmark = [pytest.mark.ui, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('header', ['strict-transport-security', 'x-content-type-options', 'frame-protection'])
def test_negative_login_response_has_transport_and_content_protections(guest_page, base_url, header):
    response = guest_page.context.request.get(base_url)
    assert response.status == 200 and response.url.startswith('https://')
    headers = response.headers
    if header == 'strict-transport-security':
        assert 'max-age=' in headers.get(header, '').lower(), 'HTTPS response has no HSTS max-age.'
    elif header == 'x-content-type-options':
        assert headers.get(header, '').lower() == 'nosniff', 'Browser content sniffing is not disabled.'
    else:
        csp = headers.get('content-security-policy', '').lower()
        assert headers.get('x-frame-options', '').lower() in ('deny', 'sameorigin') or 'frame-ancestors ' in csp, 'Login can be framed without an explicit frame policy.'


def test_negative_authenticated_identity_response_is_not_cacheable(readonly_page, review_origin):
    readonly_page.goto(review_origin + '/nolimit/app/home', wait_until='domcontentloaded')
    response = readonly_page.context.request.get(QA_API + '/auth/me', headers=session_headers(readonly_page))
    assert response.status == 200
    assert 'no-store' in response.headers.get('cache-control', '').lower(), 'Authenticated identity response is missing Cache-Control: no-store.'


def test_negative_unknown_cors_origin_cannot_read_authenticated_identity(readonly_page, review_origin):
    readonly_page.goto(review_origin + '/nolimit/app/home', wait_until='domcontentloaded')
    origin = 'https://untrusted-qa-origin.example.test'
    response = readonly_page.context.request.get(QA_API + '/auth/me', headers={
        **session_headers(readonly_page), 'Origin': origin,
    })
    assert response.status in (200, 401, 403)
    assert response.headers.get('access-control-allow-origin') not in (origin, '*'), 'Untrusted origins are authorized to read authenticated API responses.'


@pytest.mark.parametrize('method', ['TRACE', 'TRACK'])
def test_negative_diagnostic_http_methods_are_disabled(guest_page, base_url, method):
    response = guest_page.context.request.fetch(base_url, method=method, max_redirects=0)
    assert response.status in (400, 403, 404, 405, 501), f'{method} was not rejected.'
    assert b'message/http' not in response.body().lower(), 'Diagnostic response reflects request contents.'
