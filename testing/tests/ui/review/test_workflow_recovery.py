"""Connected draft/recovery workflows; the inherited fixture blocks API writes."""
import re
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from pages.mainOnboardingPage import MainOnboardingPage
from pages.screeningPage import ScreeningPage
from pages.transactionPage import TransactionPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly]


def transaction_form_values(transaction):
    """Capture both amounts and connected parties, not just the address."""
    # One atomic snapshot avoids mixing values from different async form renders.
    # This workflow needs a populated transaction with both connected parties.
    return transaction.page.wait_for_function("""() => {
        const modal = document.querySelector('.modal-z-open.style-modal:not(.document-preview-modal)');
        if (!modal) return false;
        const field = name => [...modal.querySelectorAll('.input-box')]
            .find(box => box.querySelector(`label[for="${name}"]`));
        const selected = name => [...(field(name)?.querySelectorAll('.ant-select-selection-item') || [])]
            .map(item => item.innerText.trim());
        const values = {
            inputs: [selected('property')[0] || field('property')?.querySelector('input')?.value || '',
                ...['propertyValue', 'amount'].map(name => field(name)?.querySelector('input')?.value || '')],
            choices: ['propertyType', 'paymentMethod', 'currency'].map(name => selected(name)[0] || ''),
            seller: selected('sellerClientIds'), buyer: selected('buyerClientIds'),
            date: modal.querySelector('input[placeholder="Select date and time"]')?.value || ''
        };
        if (!values.inputs[0] || !values.date || values.choices.some(value => !value)) return false;
        if (!values.seller.length || !values.buyer.length || [...values.seller, ...values.buyer].some(value => !value)) return false;
        return values;
    }""", timeout=30000).json_value()


@pytest.mark.negative
@pytest.mark.parametrize('exit_method', ['cancel', 'close', 'reload', 'navigate'])
def test_negative_transaction_edit_discard_survives_reopen(readonly_page, review_origin, exit_method):
    page = readonly_page
    page.goto(review_origin + '/nolimit/app/transaction-activities', wait_until='domcontentloaded')
    transaction = TransactionPage(page)
    transaction.open()
    transaction.require_records()
    transaction_id = transaction.open_edit_first()
    original = transaction_form_values(transaction)
    transaction.fill_field('amount', '123.45')

    if exit_method == 'cancel':
        transaction.cancel_modal()
    elif exit_method == 'close':
        transaction.close_modal()
    elif exit_method == 'reload':
        page.reload(wait_until='domcontentloaded')
    else:
        page.goto(review_origin + '/nolimit/app/profiles', wait_until='domcontentloaded')
        expect(page.get_by_role('heading', name='Profiles', exact=True)).to_be_visible()

    # A fresh navigation also verifies that no server-side save occurred.
    transaction.open()
    transaction.open_edit(transaction_id)
    assert transaction_form_values(transaction) == original
    transaction.cancel_modal()


@pytest.mark.negative
@pytest.mark.parametrize('kind', ['individual', 'entity'])
@pytest.mark.parametrize('exit_method', ['reload', 'navigate'])
def test_negative_onboarding_draft_exit_never_creates_pending_client(readonly_page, review_origin, kind, exit_method):
    page = readonly_page
    page.goto(review_origin + '/nolimit/app/onboarding', wait_until='domcontentloaded')
    onboarding = MainOnboardingPage(page)
    expect(onboarding.heading).to_be_visible()
    name = 'Unsent Workflow ' + uuid4().hex[:12]
    onboarding.choose_client(kind, name)
    onboarding.select_role(kind, 'Seller')
    expect(onboarding.proceed).to_be_enabled()
    # Proceed itself attempts POST /clients, before consent is displayed.
    # Leave this unsent draft without creating a client.
    if exit_method == 'reload':
        page.reload(wait_until='domcontentloaded')
    else:
        page.goto(review_origin + '/nolimit/app/home', wait_until='domcontentloaded')
        onboarding.return_to_onboarding()
    onboarding.open_pending()
    onboarding.search.fill(name)
    onboarding.search_button.click()
    expect(page.locator('tbody .ant-empty, .empty-table').first).to_be_visible()
    expect(onboarding.rows).to_have_count(0)


@pytest.mark.positive
@pytest.mark.parametrize('kind', ['individual', 'organization'])
def test_positive_screening_draft_navigation_does_not_start_analysis(readonly_page, review_origin, kind):
    page = readonly_page
    screening = ScreeningPage(page)
    screening.open(review_origin)
    radio = screening.individual_radio if kind == 'individual' else screening.organization_radio
    radio.check()
    screening.name_input.fill('Unsubmitted Workflow ' + uuid4().hex[:10])
    screening.ongoing.check()
    # No Analyze click: switching modules must not submit the draft.
    page.get_by_role('link', name=re.compile('Transactions')).click()
    expect(page.get_by_role('heading', name='Real Estate Transactions', exact=True)).to_be_visible()
    screening.open(review_origin)
    expect(screening.name_input).to_have_value('')
    expect(screening.ongoing).not_to_be_checked()
    expect(screening.individual_radio).to_be_checked()


@pytest.mark.negative
@pytest.mark.parametrize('failure', [500, 503, 'offline'])
def test_negative_transaction_list_failure_can_recover_without_relogin(readonly_page, review_origin, failure):
    page = readonly_page
    intercepted = []
    pattern = re.compile(r'.*/api/v1/transactions(?:\?.*)?$')

    def fail(route):
        intercepted.append(route.request.method)
        if failure == 'offline':
            route.abort('internetdisconnected')
        else:
            route.fulfill(status=failure, json={'message': 'Simulated list failure'})

    page.route(pattern, fail)
    page.goto(review_origin + '/nolimit/app/transaction-activities', wait_until='domcontentloaded')
    expect(page.get_by_role('heading', name='Real Estate Transactions', exact=True)).to_be_visible()
    expect(page.get_by_text('Simulated list failure', exact=True).first if failure != 'offline'
           else page.locator('.ant-notification-notice').first).to_be_visible()
    assert intercepted and set(intercepted) == {'GET'}
    page.unroute(pattern, fail)
    page.reload(wait_until='domcontentloaded')
    transaction = TransactionPage(page)
    transaction.require_records()
    expect(transaction.add_button).to_be_enabled()
    expect(page.locator('nav.navbar .nav-avatar p')).to_have_text(re.compile('@'))

