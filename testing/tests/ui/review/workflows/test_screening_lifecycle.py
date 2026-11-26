"""Provider calls are opt-in; resolutions apply only to a freshly created analysis."""
import os

import pytest
from playwright.sync_api import expect

from pages.screeningDailyPage import ScreeningDailyPage
from pages.screeningFunctionalPage import ScreeningFunctionalPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.screening_write]


@pytest.mark.positive
@pytest.mark.parametrize('organization', [False, True], ids=['individual', 'organization'])
def test_positive_ongoing_analysis_reload_reopen_remove_lifecycle(workflow_page, review_origin, organization):
    page = workflow_page('SCREENING', deletes=True)
    screening = ScreeningDailyPage(page)
    screening.open(review_origin)
    name = screening.unique_name()
    record = None
    try:
        record = screening.create_ongoing_record(name=name, organization=organization)
        page.reload(wait_until='domcontentloaded')
        screening.open_daily()
        row = screening.find_daily_record(name)
        assert screening.get_daily_profile_id(row) == record['profile_id']
        results = screening.open_daily_record(record)
        counts = results.wait_for_counts()
        assert sum(counts.values()) == results.count()
        screening.return_to_screening()
        screening.open_daily()
        screening.remove_ongoing_records([record])
        page.reload(wait_until='domcontentloaded')
        screening.open_daily()
        screening.assert_daily_record_absent(name)
    finally:
        # Restrict cleanup to this test's unique generated name/record.
        if record is not None:
            screening.cleanup_ongoing_record(record)
        else:
            screening.cleanup_ongoing_name(name)


@pytest.mark.positive
@pytest.mark.parametrize('destination', ['Positive Hits', 'False Hits', 'Possible Hits'])
def test_positive_new_analysis_resolution_survives_reload(workflow_page, review_origin, destination):
    page = workflow_page('SCREENING_RESOLUTIONS')
    name = os.getenv('WORKFLOW_SCREENING_MATCH_NAME', '').strip()
    assert name, 'Set WORKFLOW_SCREENING_MATCH_NAME to an approved provider test name with unresolved matches.'
    screening = ScreeningDailyPage(page)
    screening.open(review_origin)
    screening.analyze_screening(name, ongoing=False)
    results = ScreeningFunctionalPage(page)
    total = results.count()
    changed_ids = results.update_selected_records('Unresolved Hits', destination, quantity=1)
    before_reload = results.wait_for_counts()
    page.reload(wait_until='domcontentloaded')
    results.assert_loaded(name)
    assert results.wait_for_counts() == before_reload
    assert results.count() == total
    results.choose_category(destination)
    for profile_id in changed_ids:
        assert results.find_profile_across_pages(profile_id)
        results.assert_row_resolution(profile_id, destination)
    expect(results.summary).to_contain_text(name)
