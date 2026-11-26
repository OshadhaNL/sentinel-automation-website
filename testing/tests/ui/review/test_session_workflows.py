"""Client-side session recovery. Mocked expiry does not certify server TTL policy."""
import re
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly, pytest.mark.negative]

PROTECTED_PATHS = [
    'home', 'dashboard', 'onboarding', 'profiles', 'transaction-activities',
    'screening', 'activity-logs', 'access-control', 'profile-settings', 'config',
]


@pytest.mark.parametrize('path', PROTECTED_PATHS)
def test_negative_expired_session_returns_to_login(readonly_page, review_origin, path):
    rejected = []

    def expired(route):
        endpoint = urlsplit(route.request.url).path
        if '/system-settings/' in endpoint:
            route.fallback()
        else:
            # Includes refresh attempts: never revoke or refresh the shared session.
            rejected.append(endpoint)
            route.fulfill(status=401, json={'message': 'Simulated expired session'})

    readonly_page.route('**/api/**', expired)
    readonly_page.goto(review_origin + '/nolimit/app/' + path, wait_until='domcontentloaded')
    expect(readonly_page).to_have_url(re.compile(r'.*/nolimit/login/?$'), timeout=20000)
    expect(readonly_page.get_by_role('heading', name='Log in', exact=True)).to_be_visible(timeout=20000)
    expect(readonly_page.locator('main')).to_have_count(0)
    assert rejected, 'The expiry simulation was not exercised.'


@pytest.mark.parametrize('path', PROTECTED_PATHS)
def test_negative_removed_local_session_cannot_reopen_module(readonly_page, review_origin, path):
    # Only this isolated browser context changes; the real account/session stays valid.
    readonly_page.goto(review_origin + '/nolimit/app/home', wait_until='domcontentloaded')
    expect(readonly_page.get_by_role('heading', name='Welcome', exact=True)).to_be_visible(timeout=15000)
    readonly_page.evaluate("""() => {
        localStorage.removeItem('accessToken:nolimit');
        localStorage.removeItem('refreshToken:nolimit');
    }""")
    readonly_page.goto(review_origin + '/nolimit/app/' + path, wait_until='domcontentloaded')
    expect(readonly_page).to_have_url(re.compile(r'.*/nolimit/login/?$'), timeout=15000)
    expect(readonly_page.locator('main')).to_have_count(0)
    readonly_page.reload(wait_until='domcontentloaded')
    expect(readonly_page.get_by_role('heading', name='Log in', exact=True)).to_be_visible(timeout=20000)
