"""Measure real page readiness; enforce only an explicitly supplied latency budget."""
import os
import time

import pytest
from playwright.sync_api import expect


pytestmark = [pytest.mark.ui, pytest.mark.readonly, pytest.mark.performance, pytest.mark.positive]


@pytest.mark.parametrize('route', ['home', 'profiles', 'transaction-activities'])
def test_positive_page_readiness_within_agreed_budget(readonly_page, review_origin, record_property, route):
    started = time.perf_counter()
    response = readonly_page.goto(review_origin + '/nolimit/app/' + route, wait_until='domcontentloaded')
    expect(readonly_page.locator('main h1')).to_be_visible(timeout=30000)
    expect(readonly_page.locator('main .ant-spin-spinning')).to_have_count(0, timeout=30000)
    elapsed = (time.perf_counter() - started) * 1000
    assert response and response.status == 200
    record_property('route', route)
    record_property('ui_ready_ms', round(elapsed, 2))
    raw_budget = os.getenv('WORKFLOW_UI_READY_BUDGET_MS', '').strip()
    if not raw_budget:
        pytest.skip('Readiness was measured; set an agreed WORKFLOW_UI_READY_BUDGET_MS before claiming a performance pass.')
    budget = float(raw_budget)
    assert budget > 0
    assert elapsed <= budget, f'{route} took {elapsed:.0f} ms; agreed budget is {budget:.0f} ms.'
