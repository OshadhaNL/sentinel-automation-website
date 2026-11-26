"""Explicit opt-ins for persistent workflows, separate from read-only fixtures."""
import os
import json
from pathlib import Path

import pytest


@pytest.fixture
def agreed_rules():
    filename = os.getenv('WORKFLOW_RULES_FILE', '').strip()
    if not filename:
        pytest.skip('Set WORKFLOW_RULES_FILE to the approved QA business-rules JSON.')
    return json.loads(Path(filename).read_text(encoding='utf-8'))


@pytest.fixture
def workflow_page(request, browser_name):
    # Declare the browser parameter so pytest-playwright collects every selected engine.
    contexts = []

    def open_page(feature, *, deletes=False):
        if os.getenv('WORKFLOW_ALLOW_WRITES') != '1':
            pytest.skip('Set WORKFLOW_ALLOW_WRITES=1 for approved QA writes.')
        if os.getenv('WORKFLOW_DISPOSABLE_DATA_CONFIRMED') != '1':
            pytest.fail('Confirm disposable data with WORKFLOW_DISPOSABLE_DATA_CONFIRMED=1.')
        if os.getenv('WORKFLOW_' + feature) != '1':
            pytest.skip(f'Set WORKFLOW_{feature}=1 to enable this workflow.')
        if deletes and os.getenv('WORKFLOW_ALLOW_DELETES') != '1':
            pytest.skip('This lifecycle includes cleanup; set WORKFLOW_ALLOW_DELETES=1.')
        if os.getenv('PYTEST_XDIST_WORKER'):
            pytest.fail('Run persistent workflows with -n 0; supplied clients must not be shared concurrently.')
        browser = request.getfixturevalue('browser')
        state = request.getfixturevalue('review_auth_state')
        context = browser.new_context(storage_state=state)
        contexts.append(context)
        page = context.new_page()
        page.set_default_timeout(20000)
        page.set_default_navigation_timeout(45000)
        return page

    yield open_page
    for context in contexts:
        context.close()


@pytest.fixture
def transaction_workflow(workflow_page, review_origin):
    from pages.transactionPage import TransactionPage

    page = workflow_page('TRANSACTIONS')
    seller = os.getenv('WORKFLOW_TRANSACTION_SELLER', '').strip()
    buyer = os.getenv('WORKFLOW_TRANSACTION_BUYER', '').strip()
    assert seller and buyer and seller.casefold() != buyer.casefold(), (
        'Set distinct WORKFLOW_TRANSACTION_SELLER and WORKFLOW_TRANSACTION_BUYER '
        'to approved disposable clients; no automatic selection of existing parties.'
    )
    page.goto(review_origin + '/nolimit/app/transaction-activities')
    transaction = TransactionPage(page)
    transaction.open()
    return transaction, seller, buyer
