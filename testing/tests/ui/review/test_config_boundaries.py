"""Exact client validation rules observed in the deployed Config implementation."""
import re

import pytest
from playwright.sync_api import expect

from pages.reviewRequests import reject_request
from pages.settingsPage import SettingsPage


pytestmark = [pytest.mark.ui, pytest.mark.readonly, pytest.mark.boundary, pytest.mark.negative]
UNIT_MAXIMUMS = {'Minutes': 59, 'Hours': 23, 'Days': 29, 'Weeks': 4, 'Months': 12}


@pytest.fixture
def config(readonly_page, review_origin):
    settings = SettingsPage(readonly_page, review_origin)
    with readonly_page.expect_response(lambda r: '/api/v1/config?' in r.url and r.request.method == 'GET') as response:
        settings.open('Config')
    response.value.finished()
    expect(settings.main.get_by_role('switch').first).to_be_enabled(timeout=20000)
    expect(settings.main.locator('input[type="number"]').first).to_be_visible()
    return settings


def choose_unit(settings, index, unit):
    select = settings.main.locator('.ant-select').nth(index)
    select.locator('.ant-select-selector').click()
    control = select.locator('input[role="combobox"]')
    popup_id = control.get_attribute('aria-controls')
    assert popup_id
    popup = settings.page.locator(f'[id="{popup_id}"]').locator('xpath=ancestor::div[contains(@class,"ant-select-dropdown")][1]')
    popup.locator('.ant-select-item-option').filter(has_text=re.compile('^' + re.escape(unit) + '$')).click()
    expect(control).to_have_attribute('aria-expanded', 'false')


def reminder_switch(settings):
    # Two onboarding switches precede the invite reminder switch in the observed UI.
    return settings.main.get_by_role('switch').nth(2)


@pytest.mark.parametrize('unit', list(UNIT_MAXIMUMS))
@pytest.mark.parametrize('case', ['zero', 'negative', 'fractional', 'minimum', 'maximum', 'over-maximum'])
def test_boundary_invite_period_unit_limits(config, unit, case):
    settings = config
    switch = reminder_switch(settings)
    if switch.get_attribute('aria-checked') == 'true':
        switch.click()  # Local draft only; persisted with the separate Save button.
    choose_unit(settings, 0, unit)
    maximum = UNIT_MAXIMUMS[unit]
    value = {'zero': '0', 'negative': '-1', 'fractional': '1.5', 'minimum': '1',
             'maximum': str(maximum), 'over-maximum': str(maximum + 1)}[case]
    settings.main.locator('input[type="number"]').first.fill(value)
    calls = reject_request(settings.page, 'config/invite-link', 500, 'PUT')
    save = settings.main.get_by_role('button', name='Save', exact=True)
    if case in ('minimum', 'maximum', 'fractional'):
        if case == 'fractional':
            expect(settings.main.locator('input[type="number"]').first).to_have_value('1')
        save.click()
        expect(settings.page.get_by_text('Failed to update invite link settings.', exact=True).first).to_be_visible()
        assert calls == ['PUT']
    else:
        message = re.compile(r'Maximum ' + str(maximum)) if case == 'over-maximum' else re.compile('Value must be a positive whole number')
        expect(settings.main.get_by_text(message).first).to_be_visible()
        expect(save).to_be_disabled()
        assert not calls


@pytest.mark.parametrize('case', ['ascending', 'duplicate', 'descending', 'at-expiry', 'after-expiry', 'zero', 'fractional'])
def test_boundary_reminder_schedule_order_and_expiry(config, case):
    settings = config
    switch = reminder_switch(settings)
    if switch.get_attribute('aria-checked') != 'true':
        switch.click()
    numbers = settings.main.locator('input[type="number"]')
    while numbers.count() < 3:
        settings.main.get_by_role('button', name='Add Reminder', exact=False).click()
    assert numbers.count() == 3, 'Use a config fixture with exactly two reminders for this schedule test.'
    choose_unit(settings, 0, 'Minutes')
    choose_unit(settings, 1, 'Minutes')
    choose_unit(settings, 2, 'Minutes')
    values = {
        'ascending': ('3', '1', '2'), 'duplicate': ('3', '1', '1'),
        'descending': ('3', '2', '1'), 'at-expiry': ('2', '1', '2'),
        'after-expiry': ('2', '1', '3'), 'zero': ('3', '0', '2'),
        'fractional': ('3', '1.5', '2'),
    }[case]
    for index, value in enumerate(values):
        numbers.nth(index).fill(value)
    calls = reject_request(settings.page, 'config/invite-link', 500, 'PUT')
    save = settings.main.get_by_role('button', name='Save', exact=True)
    if case in ('ascending', 'fractional'):
        if case == 'fractional':
            expect(numbers.nth(1)).to_have_value('1')
        save.click()
        expect(settings.page.get_by_text('Failed to update invite link settings.', exact=True).first).to_be_visible()
        assert calls == ['PUT']
    else:
        if save.is_enabled():
            save.click()
        text = 'positive whole number' if case == 'zero' else 'before the invite expiry' if case in ('at-expiry', 'after-expiry') else 'strictly ascending|Duplicate'
        expect(settings.main.get_by_text(re.compile(text)).first).to_be_visible()
        assert not calls
