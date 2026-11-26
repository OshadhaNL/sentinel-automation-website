"""Provider outages and rejected analyses are simulated before they reach QA."""
import pytest
from playwright.sync_api import expect

from pages.reviewRequests import expect_failure_notice, reject_request
from pages.screeningPage import ScreeningPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('status', [400, 403, 422, 429, 500, 502, 503, 'offline'])
@pytest.mark.parametrize('kind', ['individual', 'organization'])
def test_negative_analysis_failure_allows_retry_without_provider_call(readonly_page, review_origin, status, kind):
    page = readonly_page
    screening = ScreeningPage(page)
    screening.open(review_origin)
    (screening.individual_radio if kind == 'individual' else screening.organization_radio).check()
    screening.name_input.fill('Unsent QA Provider Test')
    calls = reject_request(page, 'world-check/search', status, 'POST')
    screening.analyze_button.click()
    expect_failure_notice(page, status)
    expect(screening.analyze_button).to_be_enabled()
    expect(screening.name_input).to_have_value('Unsent QA Provider Test')
    assert calls == ['POST']
    if status == 'offline':
        with page.expect_event('requestfailed', predicate=lambda request: request.method == 'POST' and '/world-check/search' in request.url):
            screening.analyze_button.click()
    else:
        with page.expect_response(lambda response: response.request.method == 'POST' and '/world-check/search' in response.url):
            screening.analyze_button.click()
    expect(screening.analyze_button).to_be_enabled()
    assert calls == ['POST', 'POST']
    screening.assert_loaded()
