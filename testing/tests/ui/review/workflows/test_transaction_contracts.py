"""Financial boundaries and concurrent edits using explicit business-policy expectations."""
from decimal import Decimal, ROUND_HALF_UP

import pytest
from playwright.sync_api import expect

from pages.transactionPage import TransactionPage
from pages.transactionWorkflow import create_transaction, fill_new_transaction


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.boundary]


def require_rule(rules, key):
    value = rules.get('financial', {}).get(key)
    if value is None:
        pytest.skip(f'Financial rule {key!r} has not been agreed in WORKFLOW_RULES_FILE.')
    return value


@pytest.mark.parametrize('field', ['propertyValue', 'amount'], ids=['sale-value', 'deposit'])
@pytest.mark.parametrize('case', ['zero', 'negative', 'max-minus-step', 'max', 'max-plus-step'])
def test_boundary_financial_value_matches_agreed_rules(transaction_workflow, agreed_rules, field, case):
    transaction, seller, buyer = transaction_workflow
    prefix = 'sale' if field == 'propertyValue' else 'deposit'
    if case == 'zero':
        value, accepted = Decimal('0'), require_rule(agreed_rules, prefix + '_allows_zero')
    elif case == 'negative':
        value, accepted = Decimal('-0.01'), require_rule(agreed_rules, prefix + '_allows_negative')
    else:
        maximum = Decimal(str(require_rule(agreed_rules, prefix + '_maximum')))
        step = Decimal(str(require_rule(agreed_rules, 'currency_step')))
        assert step > 0 and maximum >= step
        value = maximum + {'max-minus-step': -step, 'max': Decimal('0'), 'max-plus-step': step}[case]
        accepted = case != 'max-plus-step'
    assert isinstance(accepted, bool)
    address = fill_new_transaction(transaction, seller, buyer)
    # Avoid accidentally testing a deposit/sale relationship at the same time.
    if field == 'propertyValue':
        if value <= 0 and (not require_rule(agreed_rules, 'deposit_allows_zero') or not require_rule(agreed_rules, 'deposit_may_exceed_sale')):
            pytest.skip('The agreed deposit relationship prevents isolating this sale-value boundary; use the relationship cases.')
        transaction.fill_field('amount', '0' if value <= 0 else str(min(value, Decimal('1'))))
    else:
        transaction.fill_field('propertyValue', str(max(value, Decimal('250000'))))
    transaction.fill_field(field, str(value))
    if accepted:
        transaction.submit_modal()
        transaction_id = transaction.find_by_address(address)['id']
        transaction.page.reload(wait_until='domcontentloaded')
        transaction.open_edit(transaction_id)
        assert Decimal(transaction.field_value(field)) == value
    else:
        transaction.active_modal.locator('button.modal-z-primary-btn').click()
        expect(transaction.page.locator('.ant-notification-notice-error, .err-meg').filter(visible=True).first).to_be_visible()
        expect(transaction.active_modal).to_be_visible()
        transaction.page.reload(wait_until='domcontentloaded')
        transaction.search(address)
        expect(transaction.page.locator('tbody .ant-empty, .empty-table').first).to_be_visible()
        expect(transaction.rows).to_have_count(0)


@pytest.mark.parametrize('deposit', ['0', '100', '100.01'], ids=['below-sale', 'equal-to-sale', 'above-sale'])
def test_boundary_deposit_sale_relationship_matches_policy(transaction_workflow, agreed_rules, deposit):
    transaction, seller, buyer = transaction_workflow
    allowed_above = require_rule(agreed_rules, 'deposit_may_exceed_sale')
    assert isinstance(allowed_above, bool)
    address = fill_new_transaction(transaction, seller, buyer)
    transaction.fill_field('propertyValue', '100')
    transaction.fill_field('amount', deposit)
    accepted = (Decimal(deposit) <= 100 or allowed_above) and (Decimal(deposit) != 0 or require_rule(agreed_rules, 'deposit_allows_zero'))
    if accepted:
        transaction.submit_modal()
        assert transaction.find_by_address(address)['id']
    else:
        transaction.active_modal.locator('button.modal-z-primary-btn').click()
        expect(transaction.page.locator('.ant-notification-notice-error, .err-meg').filter(visible=True).first).to_be_visible()
        expect(transaction.active_modal).to_be_visible()


def test_boundary_money_precision_matches_rounding_policy(transaction_workflow, agreed_rules):
    transaction, seller, buyer = transaction_workflow
    places = int(require_rule(agreed_rules, 'decimal_places'))
    policy = require_rule(agreed_rules, 'excess_precision')
    assert 0 <= places <= 6 and policy in ('reject', 'round-half-up', 'preserve')
    value = Decimal('100.' + '1' * places + '5')
    address = fill_new_transaction(transaction, seller, buyer)
    transaction.fill_field('amount', str(value))
    if policy == 'reject':
        transaction.active_modal.locator('button.modal-z-primary-btn').click()
        expect(transaction.page.locator('.ant-notification-notice-error, .err-meg').filter(visible=True).first).to_be_visible()
        expect(transaction.active_modal).to_be_visible()
    else:
        transaction.submit_modal()
        transaction_id = transaction.find_by_address(address)['id']
        transaction.page.reload(wait_until='domcontentloaded')
        transaction.open_edit(transaction_id)
        expected = value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP) if policy == 'round-half-up' else value
        assert Decimal(transaction.field_value('amount')) == expected


def test_negative_concurrent_edit_obeys_conflict_policy(transaction_workflow, agreed_rules):
    transaction, seller, buyer = transaction_workflow
    policy = require_rule(agreed_rules, 'concurrent_edit')
    assert policy in ('reject-stale', 'last-save-wins')
    transaction_id, _ = create_transaction(transaction, seller, buyer)
    other_page = transaction.page.context.new_page()
    try:
        other_page.goto(transaction.page.url, wait_until='domcontentloaded')
        other = TransactionPage(other_page)
        transaction.open_edit(transaction_id)
        other.open_edit(transaction_id)
        transaction.fill_field('amount', '11100')
        other.fill_field('amount', '22200')
        transaction.submit_modal()
        if policy == 'reject-stale':
            other.active_modal.locator('button.modal-z-primary-btn').click()
            expect(other_page.locator('.ant-notification-notice-error').first).to_be_visible()
            expect(other.edit_modal).to_be_visible()
        else:
            other.submit_modal()
        transaction.page.reload(wait_until='domcontentloaded')
        transaction.open_edit(transaction_id)
        assert Decimal(transaction.field_value('amount')) == Decimal('11100' if policy == 'reject-stale' else '22200')
    finally:
        other_page.close()
