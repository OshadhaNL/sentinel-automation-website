"""Persistence/restore checks restricted to an explicitly isolated tenant."""
import os
import re

import pytest
from playwright.sync_api import expect

from pages.reviewRequests import QA_API, session_headers
from pages.settingsPage import SettingsPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.positive]


@pytest.fixture
def isolated_config(workflow_page, review_origin):
    if os.getenv('WORKFLOW_ISOLATED_TENANT_CONFIRMED') != '1':
        pytest.skip('Tenant-wide persistence tests require WORKFLOW_ISOLATED_TENANT_CONFIRMED=1.')
    page = workflow_page('CONFIG')
    settings = SettingsPage(page, review_origin)
    settings.open('Config')
    expect(settings.main.get_by_role('switch').first).to_be_enabled(timeout=20000)
    return settings


def test_positive_source_of_funds_setting_persists_and_is_restored(isolated_config):
    settings = isolated_config
    page = settings.page
    switch = settings.main.get_by_role('switch').first
    expect(switch).to_have_attribute('aria-checked', re.compile('^(true|false)$'))
    original = switch.get_attribute('aria-checked')
    try:
        with page.expect_response(lambda r: r.request.method == 'PUT' and '/config/source-of-funds-upload' in r.url) as response:
            switch.click()
        assert response.value.status == 200
        page.reload(wait_until='domcontentloaded')
        expect(switch).to_have_attribute('aria-checked', 'false' if original == 'true' else 'true')
    finally:
        page.context.request.put(QA_API + '/config/source-of-funds-upload', headers=session_headers(page), data={'enabled': original == 'true'})
        page.reload(wait_until='domcontentloaded')
        expect(switch).to_have_attribute('aria-checked', original)


def test_positive_invite_period_and_reminder_schedule_persist_then_restore(isolated_config):
    settings = isolated_config
    page = settings.page
    headers = session_headers(page)
    original = page.context.request.get(QA_API + '/config?keys=INVITE_LINK_CONFIG', headers=headers)
    assert original.status == 200
    saved = original.json()['data']['INVITE_LINK_CONFIG']
    original_payload = {key: saved[key] for key in ('value', 'unit', 'reminders')}
    expected = {'value': 3, 'unit': 'minutes', 'reminders': {'enabled': True, 'schedule': [{'value': 1, 'unit': 'minutes'}, {'value': 2, 'unit': 'minutes'}]}}
    try:
        response = page.context.request.put(QA_API + '/config/invite-link', headers=headers, data=expected)
        assert response.status == 200
        page.reload(wait_until='domcontentloaded')
        numbers = settings.main.locator('input[type="number"]')
        for index, value in enumerate(('3', '1', '2')):
            expect(numbers.nth(index)).to_have_value(value)
        current = page.context.request.get(QA_API + '/config?keys=INVITE_LINK_CONFIG', headers=headers).json()['data']['INVITE_LINK_CONFIG']
        for key, value in expected.items():
            assert current[key] == value
    finally:
        restored = page.context.request.put(QA_API + '/config/invite-link', headers=headers, data=original_payload)
        assert restored.status == 200
