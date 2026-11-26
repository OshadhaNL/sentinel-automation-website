"""Small, opt-in GET-only concurrency check on an explicitly isolated QA tenant."""
from concurrent.futures import ThreadPoolExecutor
import math
import os
import time

import pytest
import requests

from pages.reviewRequests import QA_API, session_headers


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.performance, pytest.mark.positive]


@pytest.mark.parametrize('concurrency', [1, 3])
def test_positive_bounded_identity_api_load_meets_agreed_budget(workflow_page, review_origin, concurrency):
    if os.getenv('WORKFLOW_ISOLATED_TENANT_CONFIRMED') != '1':
        pytest.skip('Confirm the isolated tenant before enabling even bounded load checks.')
    raw_budget = os.getenv('WORKFLOW_API_P95_BUDGET_MS', '').strip()
    if not raw_budget:
        pytest.skip('Set the agreed WORKFLOW_API_P95_BUDGET_MS.')
    budget = float(raw_budget)
    assert budget > 0
    page = workflow_page('LOAD')
    page.goto(review_origin + '/nolimit/app/home', wait_until='domcontentloaded')
    headers = session_headers(page)

    def get_identity(_):
        started = time.perf_counter()
        with requests.get(QA_API + '/auth/me', headers=headers, timeout=30) as response:
            assert response.status_code == 200
            assert response.json().get('data'), 'Successful load response is missing identity data.'
        return (time.perf_counter() - started) * 1000

    # Five requests per worker, capped at 15 total; no screening/provider or writes.
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        timings = sorted(pool.map(get_identity, range(5 * concurrency)))
    p95 = timings[math.ceil(len(timings) * .95) - 1]
    assert p95 <= budget, f'Identity API p95 {p95:.0f} ms exceeds {budget:.0f} ms at concurrency {concurrency}.'
