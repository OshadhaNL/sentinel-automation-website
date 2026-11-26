"""Account and invitation failures answered locally; no account or email is created."""
import pytest
from playwright.sync_api import expect

from pages.reviewRequests import expect_failure_notice, reject_request
from pages.settingsPage import SettingsPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('status', [403, 409, 422, 429, 500, 503, 'offline'])
@pytest.mark.parametrize('kind', ['staff', 'invite'])
def test_negative_account_submission_failure_preserves_usable_form(readonly_page, review_origin, status, kind):
    page = readonly_page
    settings = SettingsPage(page, review_origin)
    if kind == 'staff':
        settings.open_add_user()
    else:
        settings.open_invite_form()
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill('Unsent')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill('QA Review')
    email = settings.modal.get_by_placeholder('Enter email address', exact=True)
    email.fill('unsent-review@example.test')
    # Staff permissions and client business roles use different dropdowns.
    role = settings.modal.locator('.ant-select').first
    role.locator('.ant-select-selector').click()
    page.locator('.ant-select-dropdown:visible .ant-select-item-option').filter(
        has_text='Client' if kind == 'staff' else 'Seller').first.click()
    # Role selection can re-render the invite form's schema; populate text after it settles.
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill('Unsent')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill('QA Review')
    expect(settings.modal.get_by_placeholder('Enter first name', exact=True)).to_have_value('Unsent')
    calls = reject_request(page, 'user-management', status, 'POST')
    submit = settings.modal.get_by_role('button', name='Add User' if kind == 'staff' else 'Send Invite', exact=True)
    submit.click()
    expect_failure_notice(page, status)
    assert calls == ['POST'], 'Submission did not exercise the simulated backend failure.'
    expect(settings.modal).to_be_visible()
    expect(submit).to_be_enabled()
    expect(email).to_be_enabled()
    # A retry is intercepted by the same handler; no real invitation is sent.
    # The invitation component clears its fields even after a failed request.
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill('Unsent')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill('QA Review')
    email.fill('unsent-review@example.test')
    role.locator('.ant-select-selector').click()
    page.locator('.ant-select-dropdown:visible .ant-select-item-option').filter(
        has_text='Client' if kind == 'staff' else 'Seller').first.click()
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill('Unsent')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill('QA Review')
    expect(settings.modal.get_by_placeholder('Enter first name', exact=True)).to_have_value('Unsent')
    if status == 'offline':
        with page.expect_event('requestfailed', predicate=lambda request: request.method == 'POST' and '/user-management' in request.url):
            submit.click()
    else:
        with page.expect_response(lambda response: response.request.method == 'POST' and '/user-management' in response.url):
            submit.click()
    expect(submit).to_be_enabled()
    assert calls == ['POST', 'POST']
    settings.cancel_modal()


@pytest.mark.boundary
@pytest.mark.parametrize('field', ['first', 'last'])
@pytest.mark.parametrize('value,valid', [('', False), ('A', False), ('AB', True), ('ABC', True), ('  A  ', False)],
                         ids=['empty', 'one-character', 'exact-two', 'three-characters', 'trimmed-one'])
def test_boundary_invite_name_uses_two_trimmed_characters(readonly_page, review_origin, field, value, valid):
    page = readonly_page
    settings = SettingsPage(page, review_origin)
    settings.open_invite_form()
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill(value if field == 'first' else 'QA')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill(value if field == 'last' else 'Review')
    settings.modal.get_by_placeholder('Enter email address', exact=True).fill('unsent-boundary@example.test')
    settings.modal.locator('.ant-select-selector').first.click()
    page.locator('.ant-select-dropdown:visible .ant-select-item-option').filter(has_text='Seller').first.click()
    calls = reject_request(page, 'user-management', 422, 'POST')
    settings.modal.get_by_role('button', name='Send Invite', exact=True).click()
    if valid:
        expect_failure_notice(page, 422)
        assert calls == ['POST']
    else:
        expect(page.locator('.err-meg, .ant-notification-notice-error').filter(visible=True).first).to_be_visible()
        assert not calls
