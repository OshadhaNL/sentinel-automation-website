"""Configuration save failures are mocked; tenant settings never change."""
import re

import pytest
from playwright.sync_api import expect

from pages.reviewRequests import FAILURE_MESSAGE, reject_request
from pages.settingsPage import SettingsPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('status', [403, 422, 500, 503])
def test_negative_config_toggle_failure_preserves_saved_setting(readonly_page, review_origin, status):
    page = readonly_page
    settings = SettingsPage(page, review_origin)
    with page.expect_response(lambda r: '/api/v1/config?' in r.url and r.request.method == 'GET'):
        settings.open('Config')
    switch = settings.main.get_by_role('switch').first
    expect(switch).to_have_attribute('aria-checked', re.compile(r'^(true|false)$'))
    before = switch.get_attribute('aria-checked')
    calls = reject_request(page, 'config', status, 'PUT')
    switch.click()
    expect(page.get_by_text('Failed to update Source of Funds uploader setting.', exact=True)).to_be_visible(timeout=15000)
    assert calls == ['PUT']
    expect(switch).to_have_attribute('aria-checked', before)
    page.reload(wait_until='domcontentloaded')
    expect(switch).to_have_attribute('aria-checked', before)
