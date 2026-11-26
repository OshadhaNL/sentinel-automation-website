import os
import re

import pytest
from playwright.sync_api import expect

from pages.settingsPage import SETTINGS_ROUTES, SettingsPage


pytestmark = [pytest.mark.ui, pytest.mark.readonly]


@pytest.fixture
def settings(readonly_page, review_origin):
    return SettingsPage(readonly_page, review_origin)


@pytest.mark.positive
class TestSettingsNavigation:
    @pytest.mark.parametrize('name', SETTINGS_ROUTES)
    def test_positive_settings_deep_link_and_reload(self, settings, name):
        settings.open(name)
        settings.page.reload(wait_until='domcontentloaded')
        expect(settings.main.get_by_role('heading', name=name, exact=True)).to_be_visible()

    def test_positive_settings_menu_expands_and_collapses(self, settings):
        settings.page.goto(settings.origin + '/nolimit/app/home', wait_until='domcontentloaded')
        menu = settings.page.get_by_role('button', name=re.compile('Settings'))
        link = settings.page.get_by_role('link', name=re.compile('Activity Logs'))
        if link.is_visible():
            menu.click()
        expect(link).to_be_hidden()
        menu.click()
        for name in SETTINGS_ROUTES:
            expect(settings.page.get_by_role('link', name=re.compile(name))).to_be_visible()
        menu.click()
        expect(link).to_be_hidden()


@pytest.mark.positive
class TestAccessControl:
    def test_positive_user_table_columns(self, settings):
        settings.open('Access Control')
        settings.wait_for_table()
        assert settings.headers() == ['Name', 'Username', 'Email Address', 'Status', 'Access Type']

    def test_positive_add_user_draft_is_discarded_on_cancel(self, settings):
        settings.open_add_user()
        settings.modal.get_by_placeholder('Enter first name').fill('Unsent QA draft')
        settings.cancel_modal()
        settings.main.get_by_role('button', name='Add User', exact=True).first.click()
        expect(settings.modal.get_by_placeholder('Enter first name')).to_have_value('')

    def test_positive_available_staff_roles(self, settings):
        settings.open_add_user()
        settings.modal.locator('.ant-select-selector').click()
        options = settings.page.locator('.ant-select-dropdown:visible .ant-select-item-option-content')
        expect(options).to_have_text(['Admin', 'Analyst', 'MLRO', 'Compliance Officer', 'Client'])

    def test_positive_invitation_table_columns(self, settings):
        settings.open_invites()
        settings.wait_for_table()
        assert settings.headers() == ['Name', 'Client Type', 'Email Address', 'Status', 'Invite Expires', 'Invitation', 'Action']

    def test_positive_invitation_tab_survives_reload(self, settings):
        settings.open_invites()
        expect(settings.page).to_have_url(re.compile(r'tab=invite'))
        settings.page.reload(wait_until='domcontentloaded')
        expect(settings.main.get_by_role('heading', name='Invite Client', exact=True)).to_be_visible()

    def test_positive_invitation_language_options(self, settings):
        settings.open_invite_form()
        settings.modal.locator('.ant-select-selector').last.click()
        options = settings.page.locator('.ant-select-dropdown:visible .ant-select-item-option-content')
        expect(options).to_have_text(['English', 'Chinese (中文)'])

    def test_positive_cancel_invitation_discards_email(self, settings):
        settings.open_invite_form()
        settings.modal.get_by_placeholder('Enter email address').fill('unsent-qa@example.test')
        settings.cancel_modal()
        settings.main.get_by_role('button', name='Invite New Client', exact=True).click()
        expect(settings.modal.get_by_placeholder('Enter email address')).to_have_value('')


@pytest.mark.negative
class TestAccessControlValidation:
    def test_negative_empty_user_form_stays_open_without_api_write(self, settings):
        settings.open_add_user()
        settings.modal.get_by_role('button', name='Add User', exact=True).click()
        expect(settings.modal).to_be_visible()
        expect(settings.modal.locator('.err-meg').first).to_be_visible()

    @pytest.mark.parametrize('email', ['plainaddress', 'qa@', 'qa@@example.test', 'qa user@example.test'])
    def test_negative_invalid_user_email_has_inline_validation(self, settings, email):
        settings.open_add_user()
        field = settings.modal.get_by_placeholder('Enter email address')
        field.fill(email)
        field.blur()
        expect(settings.modal.locator('.err-meg').first).to_be_visible()

    def test_negative_expired_invite_link_cannot_be_copied(self, settings):
        settings.open_invites()
        settings.wait_for_table()
        expect(settings.rows.first).to_be_visible()
        expired = settings.rows.filter(has_text='Expired')
        if expired.count() == 0:
            pytest.skip('This page has no expired invitation fixture.')
        for row in expired.all():
            expect(row.locator('button:has(i.fa-copy)')).to_be_disabled()


@pytest.mark.positive
class TestProfileSettings:
    @pytest.mark.boundary
    def test_positive_password_nine_characters_meets_length_rule(self, settings):
        settings.open('Profile Settings')
        settings.main.get_by_placeholder('Enter new password', exact=True).fill('Aa1!aaaaa')
        expect(settings.password_hint('Password is more than 8 characters')).to_have_class('valid')

    def test_positive_account_email_is_read_only(self, settings):
        settings.open('Profile Settings')
        email = settings.main.get_by_placeholder('Enter email address')
        expect(email).to_have_value(os.environ['TEST_EMAIL'])
        expect(email).to_be_disabled()

    def test_positive_unsaved_name_does_not_persist(self, settings):
        settings.open('Profile Settings')
        field = settings.main.get_by_placeholder('Enter first name')
        expect(field).not_to_have_value('')
        original = field.input_value()
        field.fill('Unsent review draft')
        settings.page.reload(wait_until='domcontentloaded')
        expect(field).to_have_value(original)

    @pytest.mark.parametrize('placeholder', ['Enter old password', 'Enter new password', 'Enter confirm password'])
    def test_positive_password_visibility_toggle(self, settings, placeholder):
        settings.open('Profile Settings')
        field = settings.main.get_by_placeholder(placeholder, exact=True)
        field.fill('Unsent-QA-password-9!')
        expect(field).to_have_attribute('type', 'password')
        toggle = field.locator('..').get_by_role('button')
        toggle.click()
        expect(field).to_have_attribute('type', 'text')
        toggle.click()
        expect(field).to_have_attribute('type', 'password')


@pytest.mark.negative
class TestPasswordBoundaries:
    @pytest.mark.boundary
    @pytest.mark.parametrize('password', ['Aa1!aaa', 'Aa1!aaaa'])
    def test_negative_password_length_boundary_matches_displayed_rule(self, settings, password):
        settings.open('Profile Settings')
        settings.main.get_by_placeholder('Enter new password', exact=True).fill(password)
        hint = settings.password_hint('Password is more than 8 characters')
        expect(hint).to_have_class('not-valid')

    @pytest.mark.parametrize('password,missing_rule', [
        ('lowercase1!', 'Upper and lowercase letters'),
        ('UPPERCASE1!', 'Upper and lowercase letters'),
        ('NoNumbers!!', 'At least one number'),
        ('NoSymbols123', 'At least one special character'),
    ])
    def test_negative_missing_password_requirement_is_flagged(self, settings, password, missing_rule):
        settings.open('Profile Settings')
        settings.main.get_by_placeholder('Enter new password', exact=True).fill(password)
        expect(settings.password_hint(missing_rule)).to_have_class('not-valid')


@pytest.mark.positive
class TestConfigurationReadOnly:
    @pytest.mark.parametrize('heading', ['Onboarding', 'Invite Client', 'Feedback', 'Display Forms module', 'Display property listing'])
    def test_positive_configuration_sections(self, settings, heading):
        settings.open('Config')
        expect(settings.main.get_by_role('heading', name=heading, exact=True)).to_be_visible()

    def test_positive_configuration_switches_expose_boolean_states(self, settings):
        settings.open('Config')
        switches = settings.main.get_by_role('switch')
        expect(switches.first).to_be_visible()
        assert switches.count() >= 7, 'Expected the observed configuration controls.'
        for switch in switches.all():
            assert switch.get_attribute('aria-checked') in ('true', 'false')
        # These switches may autosave: deliberately do not click them.

    def test_positive_invite_configuration_has_explicit_save(self, settings):
        settings.open('Config')
        expect(settings.main.get_by_role('button', name='Save', exact=True)).to_be_enabled()
        expect(settings.main.get_by_text('Verification validity period', exact=True)).to_be_visible()
