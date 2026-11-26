"""Resume and full completion workflows for explicitly supplied disposable clients."""
import os
import re
from urllib.parse import quote
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from pages.clientReusePage import ClientReusePage
from pages.entityOnboardingPage import EntityOnboardingPage
from pages.individualOnboardingPage import IndividualOnboardingPage
from pages.mainOnboardingPage import MainOnboardingPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write]


@pytest.mark.positive
@pytest.mark.parametrize('kind', ['individual', 'entity'])
def test_positive_new_client_reopens_same_id_after_interruption(workflow_page, review_origin, kind):
    page = workflow_page('ONBOARDING')
    page.goto(review_origin + '/nolimit/app/onboarding')
    onboarding = MainOnboardingPage(page)
    name = 'QA Workflow ' + uuid4().hex[:12]
    onboarding.open_consent(kind, name, role='Seller')
    onboarding.consent_checkbox().check()
    onboarding.consent_agree().click()
    if kind == 'individual':
        individual = IndividualOnboardingPage(page)
        individual.verify_page_loaded()
        reference_id = individual.risk_get_current_client_id()
    else:
        entity = EntityOnboardingPage(page)
        entity.verify_page_loaded()
        expect(entity.reference_id).to_have_text(re.compile(r'SENTINEL\w+'))
        reference_id = entity.reference_id.inner_text().strip()

    onboarding.return_to_onboarding()
    onboarding.open_pending()
    onboarding.search.fill(reference_id)
    onboarding.search_button.click()
    onboarding.wait_for_reference_search(reference_id)
    link = onboarding.rows.get_by_role('link', name=reference_id, exact=True)
    expect(link).to_have_count(1)
    link.click()
    expect(page).to_have_url(re.compile(r'[?&]client=' + re.escape(reference_id) + r'(?:&|$)'))
    page.reload()
    if kind == 'individual':
        individual.verify_page_loaded()
        assert individual.risk_get_current_client_id() == reference_id
    else:
        entity.verify_page_loaded()
        expect(entity.reference_id).to_have_text(reference_id)
        expect(entity.client_name).to_have_text(name)


@pytest.mark.positive
def test_positive_verified_individual_kyc_risk_completion_and_profile(workflow_page, review_origin):
    page = workflow_page('ONBOARDING_COMPLETION')
    client_id = os.getenv('WORKFLOW_VERIFIED_PENDING_CLIENT_ID', '').strip()
    assert re.fullmatch(r'SENTINEL[A-Za-z0-9]+', client_id), (
        'Set WORKFLOW_VERIFIED_PENDING_CLIENT_ID to an approved disposable individual '
        'with verification completed, still pending onboarding.'
    )
    page.goto(review_origin + '/nolimit/app/onboarding')
    ClientReusePage(page).reopen_pending_individual(client_id)
    individual = IndividualOnboardingPage(page)
    individual.open_kyc_form()
    individual.kyc_assert_loaded()
    # Existing helper checks the saved text, addresses, dropdowns and wealth after reload.
    individual.kyc_51_verify_save_persistence()
    assert individual.risk_get_current_client_id() == client_id
    individual.open_risk_assessment()
    low_risk = {
        'Australian Residential Status': 'residence',
        'Transfer of Funds': 'bankTransfer',
        'Adverse Media': 'noHits',
        'Politically Exposed Person (PEP) Status': 'nonPep',
        'Country / Jurisdiction Risk': 'low',
    }
    individual.risk_select_multiple(low_risk)
    individual.risk_verify_calculation()
    individual.risk_complete_onboarding()
    individual.risk_verify_onboarding_completed()
    page.reload()
    individual.open_risk_assessment()
    individual.risk_verify_selected_values(low_risk)
    individual.risk_verify_onboarding_completed()
    individual.profiles_open_page()
    individual.profiles_search_client(client_id)
    individual.profiles_open_individual(client_id)
    individual.profile_verify_verification_page(client_id)
    expect(page).to_have_url(re.compile(re.escape(quote(client_id))))
