"""Calendar limits confirmed in the deployed frontend, relative to browser-local today."""
from datetime import date, timedelta
import re

import pytest
from playwright.sync_api import expect

from pages.transactionPage import TransactionPage


pytestmark = [pytest.mark.ui, pytest.mark.readonly, pytest.mark.boundary]


@pytest.mark.parametrize('module', ['transactions', 'profiles'])
@pytest.mark.parametrize('offset,disabled', [
    pytest.param(-1, False, id='yesterday', marks=pytest.mark.positive),
    pytest.param(0, False, id='today', marks=pytest.mark.positive),
    pytest.param(1, True, id='tomorrow', marks=pytest.mark.negative),
])
def test_boundary_future_dates_disabled_in_record_and_filter_calendars(readonly_page, review_origin, module, offset, disabled):
    page = readonly_page
    path = 'transaction-activities' if module == 'transactions' else 'profiles'
    page.goto(review_origin + '/nolimit/app/' + path, wait_until='domcontentloaded')
    if module == 'transactions':
        transaction = TransactionPage(page)
        transaction.open_add_modal()
        transaction.active_modal.get_by_placeholder('Select date and time').click()
    else:
        expect(page.get_by_role('heading', name='Profiles', exact=True)).to_be_visible()
        page.get_by_placeholder('Start Date', exact=True).click()
    year, month, day = page.evaluate('() => { const d = new Date(); return [d.getFullYear(), d.getMonth()+1, d.getDate()]; }')
    target = (date(year, month, day) + timedelta(days=offset)).isoformat()
    cell = page.locator(f'.ant-picker-dropdown:visible td[title="{target}"]').first
    expect(cell).to_be_visible()
    if disabled:
        expect(cell).to_have_class(re.compile(r'\bant-picker-cell-disabled\b'))
    else:
        expect(cell).not_to_have_class(re.compile(r'\bant-picker-cell-disabled\b'))
