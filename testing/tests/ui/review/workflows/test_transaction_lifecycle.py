"""Fresh transactions only. Saved test records remain for audit; no silent deletion."""
import re
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.transactionWorkflow import create_transaction, fill_new_transaction


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write]


@pytest.mark.positive
def test_positive_create_edit_reload_preserves_id_fields_and_parties(transaction_workflow):
    transaction, seller, buyer = transaction_workflow
    transaction_id, address = create_transaction(transaction, seller, buyer)
    transaction.open_edit(transaction_id)
    transaction.choose_or_create_property(address + ' edited')
    transaction.fill_field('propertyValue', '300000.75')
    transaction.fill_field('amount', '30000.25')
    transaction.select_option('propertyType', 'Commercial')
    transaction.select_option('paymentMethod', 'Cash')
    transaction.select_currency('USD')
    transaction.submit_modal()
    transaction.page.reload()
    transaction.open_edit(transaction_id)
    expect(transaction.dropdown_for('property').locator('.ant-select-selection-item')).to_have_text(address + ' edited')
    assert Decimal(transaction.field_value('propertyValue')) == Decimal('300000.75')
    assert Decimal(transaction.field_value('amount')) == Decimal('30000.25')
    assert 'Commercial' in transaction.selected_option('propertyType')
    assert 'Cash' in transaction.selected_option('paymentMethod')
    assert 'USD' in transaction.selected_option('currency')
    expect(transaction.party_tags('seller')).to_contain_text([seller])
    expect(transaction.party_tags('buyer')).to_contain_text([buyer])
    transaction.cancel_modal()
    transaction.search_for_record(transaction_id)
    expect(transaction.table_row(transaction_id)).to_have_count(1)


@pytest.mark.negative
@pytest.mark.parametrize('failure', [500, 'offline'])
def test_negative_failed_edit_preserves_saved_record_then_retry_succeeds(transaction_workflow, failure):
    transaction, seller, buyer = transaction_workflow
    page = transaction.page
    transaction_id, address = create_transaction(transaction, seller, buyer)
    transaction.open_edit(transaction_id)
    transaction.choose_or_create_property(address + ' recovered')
    blocked = []
    pattern = re.compile(r'.*/api/v1/transactions(?:/[^?]*)?(?:\?.*)?$')

    def fail_write(route):
        if route.request.method in ('POST', 'PUT', 'PATCH'):
            blocked.append(route.request.method)
            if failure == 'offline':
                route.abort('internetdisconnected')
            else:
                route.fulfill(status=500, json={'message': 'Simulated transaction save failure'})
        else:
            route.fallback()

    page.route(pattern, fail_write)
    transaction.active_modal.locator('button.modal-z-primary-btn').click()
    expect(page.locator('.ant-notification-notice').first).to_be_visible()
    assert blocked, 'The save request did not reach the simulated failure.'
    expect(transaction.edit_modal).to_be_visible()
    expect(transaction.dropdown_for('property').locator('.ant-select-selection-item')).to_have_text(address + ' recovered')
    expect(transaction.active_modal.locator('button.modal-z-primary-btn')).to_be_enabled()
    page.unroute(pattern, fail_write)
    # Read the durable original in another tab before retrying the still-open draft.
    other = page.context.new_page()
    try:
        from pages.transactionPage import TransactionPage
        other.goto(page.url)
        saved = TransactionPage(other)
        saved.open()
        saved.open_edit(transaction_id)
        expect(saved.dropdown_for('property').locator('.ant-select-selection-item')).to_have_text(address)
    finally:
        other.close()
    transaction.submit_modal()
    page.reload()
    transaction.open_edit(transaction_id)
    expect(transaction.dropdown_for('property').locator('.ant-select-selection-item')).to_have_text(address + ' recovered')


@pytest.mark.negative
def test_negative_double_submit_creates_exactly_one_transaction(transaction_workflow):
    transaction, seller, buyer = transaction_workflow
    address = fill_new_transaction(transaction, seller, buyer)
    transaction.active_modal.locator('button.modal-z-primary-btn').dblclick()
    expect(transaction.active_modal).to_be_hidden(timeout=30000)
    transaction.search_for_record(address, column=1)
    matching = transaction.rows.filter(has_text=address)
    expect(matching).to_have_count(1)
    transaction_id = transaction.first_transaction_id()
    transaction.page.reload()
    transaction.search_for_record(address, column=1)
    expect(transaction.rows.filter(has_text=address)).to_have_count(1)
    assert transaction.first_transaction_id() == transaction_id
