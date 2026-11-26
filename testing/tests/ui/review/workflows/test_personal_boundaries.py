"""Name, age and document-expiry boundaries on a dedicated, valid disposable KYC form."""
import calendar
from datetime import date, timedelta
import os
import re
from urllib.parse import quote

import pytest
from playwright.sync_api import expect

from pages.individualOnboardingPage import IndividualOnboardingPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.boundary]


def rule(rules, key):
    value = rules.get('person', {}).get(key)
    if value is None:
        pytest.skip(f'Personal-data rule {key!r} is not agreed in WORKFLOW_RULES_FILE.')
    return value


@pytest.fixture
def personal_form(workflow_page, review_origin, agreed_rules):
    client = os.getenv('WORKFLOW_KYC_BOUNDARY_CLIENT_ID', '').strip()
    assert re.fullmatch(r'SENTINEL[A-Za-z0-9]+', client), 'Supply a disposable verified client with a valid, already saved KYC form.'
    assert client != os.getenv('WORKFLOW_VERIFIED_PENDING_CLIENT_ID'), 'Boundary and completion workflows must use different clients.'
    page = workflow_page('PERSONAL_BOUNDARIES')
    page.goto(review_origin + '/nolimit/app/onboarding/individual/process?step=kyc-form&client=' + quote(client), wait_until='domcontentloaded')
    individual = IndividualOnboardingPage(page)
    individual.verify_page_loaded()
    individual.open_kyc_form()
    individual.kyc_assert_loaded()
    expect(individual.kyc_text_input('full_name')).not_to_have_value('')
    return individual, client


def save_valid_form(individual, client):
    with individual.page.expect_response(lambda r: r.request.method == 'PUT' and f'/clients/{client}/kyc-form' in r.url) as pending:
        individual.kyc_click_save()
    response = pending.value
    assert 200 <= response.status < 300, 'KYC save rejected a value expected to be accepted.'
    assert response.json().get('success') is not False
    individual.page.wait_for_load_state('networkidle', timeout=30000)


def assert_field_case(individual, client, control, value, accepted, expected=None):
    assert isinstance(accepted, bool)
    original = control.input_value()
    try:
        control.fill(value)
        control.press('Tab')
        if accepted:
            save_valid_form(individual, client)
        else:
            individual.kyc_click_save()
            expect(individual.page.locator('.ant-notification-notice-error, .err-meg').filter(visible=True).first).to_be_visible()
        individual.page.reload(wait_until='domcontentloaded')
        individual.open_kyc_form()
        expect(control).to_have_value((expected if expected is not None else value) if accepted else original)
    finally:
        individual.page.reload(wait_until='domcontentloaded')
        individual.open_kyc_form()
        expect(control).to_be_visible()
        # Restore the dedicated client even if the tested value was wrongly accepted.
        if control.input_value() != original:
            control.fill(original)
            control.press('Tab')
            save_valid_form(individual, client)


@pytest.mark.parametrize('bound', ['name_min', 'name_max'])
@pytest.mark.parametrize('offset', [-1, 0, 1], ids=['minus-one', 'exact', 'plus-one'])
def test_boundary_name_length_matches_agreed_limit(personal_form, agreed_rules, bound, offset):
    individual, client = personal_form
    limit = int(rule(agreed_rules, bound))
    assert 1 <= limit <= 10000
    value = 'A' * (limit + offset)
    minimum, maximum = int(rule(agreed_rules, 'name_min')), int(rule(agreed_rules, 'name_max'))
    assert 1 <= minimum <= maximum <= 10000
    accepted = minimum <= len(value) <= maximum
    assert_field_case(individual, client, individual.kyc_text_input('full_name'), value, accepted)


@pytest.mark.parametrize('value,key', [
    ('Anne-Marie Review', 'hyphenated_name_allowed'),
    ("O'Connor Review", 'apostrophe_name_allowed'),
    ('José 漢字 Review', 'unicode_name_allowed'),
    ('  QA Review  ', 'whitespace_name_allowed'),
])
def test_boundary_name_character_rules_and_normalization(personal_form, agreed_rules, value, key):
    individual, client = personal_form
    accepted = rule(agreed_rules, key)
    trim = rule(agreed_rules, 'trim_names')
    assert isinstance(trim, bool)
    assert_field_case(individual, client, individual.kyc_text_input('full_name'), value, accepted, value.strip() if trim else value)


@pytest.mark.parametrize('offset', [-1, 0, 1], ids=['one-day-older', 'exact-age', 'one-day-younger'])
def test_boundary_minimum_age_matches_birthday_rule(personal_form, agreed_rules, offset):
    individual, client = personal_form
    years = int(rule(agreed_rules, 'minimum_age'))
    assert 0 < years < 150
    today = date(*individual.page.evaluate('() => {const d=new Date();return [d.getFullYear(),d.getMonth()+1,d.getDate()];}'))
    year = today.year - years
    if today.month == 2 and today.day == 29 and not calendar.isleap(year):
        leap_rule = rule(agreed_rules, 'leap_birthday')
        assert leap_rule in ('feb28', 'mar1')
        threshold = date(year, 2, 28) if leap_rule == 'feb28' else date(year, 3, 1)
    else:
        threshold = today.replace(year=year)
    value = (threshold + timedelta(days=offset)).strftime('%d-%m-%Y')
    assert_field_case(individual, client, individual.kyc_date_input(0), value, offset <= 0)


@pytest.mark.parametrize('case', ['future-dob', 'leap-day-dob', 'expiry-yesterday', 'expiry-today', 'expiry-tomorrow'])
def test_boundary_birth_and_expiry_dates_match_agreed_policy(personal_form, agreed_rules, case):
    individual, client = personal_form
    today = date(*individual.page.evaluate('() => {const d=new Date();return [d.getFullYear(),d.getMonth()+1,d.getDate()];}'))
    if case == 'future-dob':
        target, index, key = today + timedelta(days=1), 0, 'future_dob_allowed'
    elif case == 'leap-day-dob':
        year = today.year - int(rule(agreed_rules, 'minimum_age')) - 4
        while not calendar.isleap(year):
            year -= 1
        target, index, key = date(year, 2, 29), 0, 'leap_day_dob_allowed'
    else:
        offset = {'expiry-yesterday': -1, 'expiry-today': 0, 'expiry-tomorrow': 1}[case]
        target, index, key = today + timedelta(days=offset), 2, case.replace('-', '_') + '_allowed'
    accepted = rule(agreed_rules, key)
    assert_field_case(individual, client, individual.kyc_date_input(index), target.strftime('%d-%m-%Y'), accepted)
