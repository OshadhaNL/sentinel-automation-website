import uuid

import pytest
from playwright.sync_api import expect

from pages.settingsPage import SettingsPage


pytestmark = [pytest.mark.ui, pytest.mark.readonly]


@pytest.fixture
def activity(readonly_page, review_origin):
    page = SettingsPage(readonly_page, review_origin)
    page.open('Activity Logs')
    page.wait_for_table()
    # These list/detail checks require an existing audit-log fixture. Waiting
    # for it also prevents the initial loading placeholder being read as empty.
    expect(page.rows.first).to_be_visible(timeout=15000)
    return page


@pytest.mark.positive
def test_positive_activity_log_columns(activity):
    assert activity.headers() == ['Date & Time', 'Client ID', 'Activity', 'Actioned By', 'Description', 'Details']


@pytest.mark.positive
def test_positive_activity_log_filter_controls(activity):
    expect(activity.main.get_by_placeholder('Search by Client ID or Document name')).to_be_enabled()
    expect(activity.main.get_by_placeholder('Start Date')).to_be_visible()
    expect(activity.main.get_by_placeholder('End Date')).to_be_visible()
    expect(activity.main.get_by_role('button', name='Extract', exact=False)).to_be_enabled()


@pytest.mark.negative
def test_negative_unknown_activity_search_has_empty_state(activity):
    search = activity.main.get_by_placeholder('Search by Client ID or Document name')
    search.fill('review-no-match-' + uuid.uuid4().hex)
    activity.main.locator('button.search-btn').click()
    expect(activity.rows).to_have_count(0)
    expect(activity.empty_state).to_be_visible()


@pytest.mark.positive
def test_positive_activity_search_clear_recovers_results(activity):
    search = activity.main.get_by_placeholder('Search by Client ID or Document name')
    search.fill('review-no-match-' + uuid.uuid4().hex)
    activity.main.locator('button.search-btn').click()
    expect(activity.empty_state).to_be_visible()
    activity.main.locator('button.clear-btn').click()
    expect(search).to_have_value('')
    activity.wait_for_table()
    expect(activity.rows.first).to_be_visible()


@pytest.mark.positive
def test_positive_activity_details_open_and_close(activity):
    activity.rows.first.get_by_role('button').click()
    expect(activity.modal.get_by_text('Description', exact=True)).to_be_visible()
    expect(activity.modal.get_by_text('Details', exact=True)).to_be_visible()
    activity.modal.locator('button').first.click()
    expect(activity.modal).to_have_count(0)


@pytest.mark.boundary
@pytest.mark.negative
def test_negative_activity_previous_disabled_on_first_page(activity):
    expect(activity.main.locator('.ant-pagination-prev button')).to_be_disabled()


@pytest.mark.positive
def test_positive_activity_pagination_round_trip(activity):
    next_button = activity.main.locator('.ant-pagination-next button')
    if next_button.is_disabled():
        pytest.skip('At least two pages of activity logs are needed.')
    next_button.click()
    expect(activity.main.locator('.ant-pagination-item-active')).to_have_attribute('title', '2')
    activity.main.locator('.ant-pagination-prev button').click()
    expect(activity.main.locator('.ant-pagination-item-active')).to_have_attribute('title', '1')


@pytest.mark.negative
@pytest.mark.parametrize('search_text', [' ', '   ', '日本語', "O'Reilly", '<review-not-html>', 'a' * 256])
def test_negative_activity_search_input_is_plain_text(activity, search_text):
    search = activity.main.get_by_placeholder('Search by Client ID or Document name')
    search.fill(search_text)
    expect(search).to_have_value(search_text)
    expect(activity.main.locator('review-not-html')).to_have_count(0)
    # Do not assume undocumented maximum lengths or execute injection payloads.
