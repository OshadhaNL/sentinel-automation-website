import re

import pytest
from playwright.sync_api import expect

from pages.loginPage import LoginPage


pytestmark = [pytest.mark.ui, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('status', [401, 429, 500, 503])
def test_negative_login_error_keeps_credentials_form_usable(guest_page, base_url, status):
    calls = []

    def respond(route):
        calls.append(route.request.method)
        route.fulfill(status=status, json={'message': 'Simulated QA login failure'})

    # All attempts are answered locally: no failed login reaches the QA server.
    guest_page.route('**/api/v1/auth/login', respond)
    login = LoginPage(guest_page)
    login.open(base_url)
    login.login('unsent-review@example.test', 'Unsent-QA-password-9!')
    # Rate limiting uses an Ant Design warning message rather than an error notice.
    expect(guest_page.get_by_text('Simulated QA login failure', exact=True)).to_be_visible()
    expect(login.login_button).to_be_enabled()
    expect(login.email_input).to_be_enabled()
    expect(login.password_input).to_be_enabled()
    login.verify_still_on_login_page()
    assert calls == ['POST']


def test_negative_login_network_failure_allows_retry(guest_page, base_url):
    calls = []

    def offline(route):
        calls.append(route.request.method)
        route.abort('internetdisconnected')

    guest_page.route('**/api/v1/auth/login', offline)
    login = LoginPage(guest_page)
    login.open(base_url)
    login.login('unsent-review@example.test', 'Unsent-QA-password-9!')
    expect(login.error_notification.first).to_be_visible()
    expect(login.login_button).to_be_enabled()
    login.verify_still_on_login_page()
    assert calls == ['POST']
    guest_page.unroute('**/api/v1/auth/login', offline)
    guest_page.route('**/api/v1/auth/login', lambda route: route.fulfill(
        status=401, json={'message': 'Simulated retry rejected'}))
    # The app clears both fields after a failed attempt; re-enter before retrying.
    login.login('unsent-review@example.test', 'Unsent-QA-password-9!')
    expect(guest_page.get_by_text('Simulated retry rejected', exact=True)).to_be_visible()


@pytest.mark.parametrize('path', [
    '/nolimit/app/onboarding',
    '/nolimit/app/profiles',
    '/nolimit/app/transaction-activities',
    '/nolimit/app/screening',
    '/nolimit/app/activity-logs',
    '/nolimit/app/access-control',
    '/nolimit/app/access-control?tab=invite',
    '/nolimit/app/profile-settings',
    '/nolimit/app/config',
])
def test_negative_other_modules_require_authentication(guest_page, review_origin, path):
    # Home and Dashboard are already covered in the original suite.
    guest_page.goto(review_origin + path, wait_until='domcontentloaded')
    expect(guest_page).to_have_url(re.compile(r'.*/nolimit/login/?$'), timeout=15000)
    expect(guest_page.get_by_role('heading', name='Log in', exact=True)).to_be_visible()
    expect(guest_page.locator('main')).to_have_count(0)
