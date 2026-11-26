from playwright.sync_api import expect


SETTINGS_ROUTES = {
    'Activity Logs': '/nolimit/app/activity-logs',
    'Access Control': '/nolimit/app/access-control',
    'Profile Settings': '/nolimit/app/profile-settings',
    'Config': '/nolimit/app/config',
}


class SettingsPage:
    def __init__(self, page, origin):
        self.page = page
        self.origin = origin
        self.main = page.locator('main')
        self.modal = page.locator('.modal-z-open .modal-z-card').filter(visible=True)
        self.rows = self.main.locator('tbody tr.ant-table-row')
        self.empty_state = self.main.locator('.empty-table')

    def open(self, name):
        self.page.goto(self.origin + SETTINGS_ROUTES[name], wait_until='domcontentloaded')
        expect(self.main.get_by_role('heading', name=name, exact=True)).to_be_visible(timeout=15000)

    def open_add_user(self):
        self.open('Access Control')
        self.main.get_by_role('button', name='Add User', exact=True).first.click()
        expect(self.modal.get_by_role('heading', name='Add User', exact=True)).to_be_visible()

    def open_invites(self):
        self.open('Access Control')
        self.main.locator('.tab-z-option').filter(has_text='Invite Client').click()
        expect(self.main.get_by_role('heading', name='Invite Client', exact=True)).to_be_visible()

    def open_invite_form(self):
        self.open_invites()
        self.main.get_by_role('button', name='Invite New Client', exact=True).click()
        expect(self.modal.get_by_role('heading', name='Invite New Client', exact=True)).to_be_visible()

    def cancel_modal(self):
        self.modal.get_by_role('button', name='Cancel', exact=True).click()
        expect(self.modal).to_have_count(0)

    def wait_for_table(self):
        # A real empty response is different from a table that has not loaded.
        expect(self.main.locator('tbody tr.ant-table-row, .empty-table, tbody .ant-empty').first).to_be_visible()

    def headers(self):
        expect(self.main.locator('thead th').first).to_be_visible()
        return [text.strip() for text in self.main.locator('thead th').all_text_contents() if text.strip()]

    def password_hint(self, text):
        return self.main.locator('li').filter(has_text=text)
