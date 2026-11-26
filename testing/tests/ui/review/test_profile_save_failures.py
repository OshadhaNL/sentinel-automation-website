"""Unsaved profile/password failures; all PUTs are answered inside the browser."""
import pytest
from playwright.sync_api import expect

from pages.reviewRequests import expect_failure_notice, reject_request
from pages.settingsPage import SettingsPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('status', [403, 409, 422, 500, 503, 'offline'])
def test_negative_profile_save_failure_does_not_change_saved_name(readonly_page, review_origin, status):
    page = readonly_page
    settings = SettingsPage(page, review_origin)
    settings.open('Profile Settings')
    name = settings.main.get_by_placeholder('Enter first name', exact=True)
    expect(name).not_to_have_value('')
    original = name.input_value()
    name.fill('Unsent QA Name')
    calls = reject_request(page, 'auth/profile', status, 'PUT')
    submit = settings.main.get_by_role('button', name='Save Changes', exact=True)
    submit.click()
    expect_failure_notice(page, status)
    assert calls == ['PUT']
    expect(submit).to_be_enabled()
    page.reload(wait_until='domcontentloaded')
    expect(name).to_have_value(original)


@pytest.mark.parametrize('status', [400, 403, 422, 429, 500, 503, 'offline'])
def test_negative_password_failure_keeps_change_form_usable(readonly_page, review_origin, status):
    page = readonly_page
    settings = SettingsPage(page, review_origin)
    settings.open('Profile Settings')
    settings.main.get_by_placeholder('Enter old password', exact=True).fill('Unsent-Old-Password-8!')
    settings.main.get_by_placeholder('Enter new password', exact=True).fill('Unsent-New-Password-9!')
    settings.main.get_by_placeholder('Enter confirm password', exact=True).fill('Unsent-New-Password-9!')
    calls = reject_request(page, 'auth/change-password', status, 'PUT')
    submit = settings.main.get_by_role('button', name='Change Password', exact=True)
    submit.click()
    expect_failure_notice(page, status)
    assert calls == ['PUT']
    expect(submit).to_be_enabled()
    expect(settings.main.get_by_placeholder('Enter old password', exact=True)).to_be_enabled()
