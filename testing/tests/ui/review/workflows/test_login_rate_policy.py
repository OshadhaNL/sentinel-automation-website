"""Real attempt-boundary and recovery checks; dedicated account and exact policy required."""
import os
import secrets
import time

import pytest

from pages.reviewRequests import QA_API


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.negative]


@pytest.mark.parametrize('case', ['attempt-boundary', 'recovery'])
def test_negative_login_rate_limit_matches_approved_policy(request, browser_name, agreed_rules, case):
    if os.getenv('WORKFLOW_LOGIN_RATE_POLICY') != '1' or os.getenv('WORKFLOW_ALLOW_WRITES') != '1':
        pytest.skip('Set WORKFLOW_LOGIN_RATE_POLICY=1 and WORKFLOW_ALLOW_WRITES=1 for the dedicated lockout account.')
    assert os.getenv('WORKFLOW_DISPOSABLE_DATA_CONFIRMED') == '1'
    assert not os.getenv('PYTEST_XDIST_WORKER'), 'Run lockout cases with -n 0.'
    email = os.getenv('WORKFLOW_RATE_EMAIL', '').strip()
    password = os.getenv('WORKFLOW_RATE_PASSWORD')
    assert email and password and email.casefold() != os.getenv('TEST_EMAIL', '').casefold()
    rules = agreed_rules.get('login', {})
    for key in ('maximum_failed_attempts', 'lockout_seconds', 'recovery_tolerance_seconds', 'lockout_status'):
        if rules.get(key) is None:
            pytest.skip(f'Confirm login.{key} in WORKFLOW_RULES_FILE.')
    attempts, duration = rules['maximum_failed_attempts'], rules['lockout_seconds']
    tolerance, status = rules['recovery_tolerance_seconds'], rules['lockout_status']
    assert isinstance(attempts, int) and 1 <= attempts <= 10
    assert isinstance(duration, int) and 1 <= duration <= 300
    assert isinstance(tolerance, int) and 0 <= tolerance <= 30
    assert status in (403, 429)
    assert os.getenv('WORKFLOW_RATE_LIMIT_SCOPE_CONFIRMED') == 'account', 'Confirm the policy is account-scoped, so other QA users are not rate-limited.'
    playwright = request.getfixturevalue('playwright')
    api = playwright.request.new_context(extra_http_headers={'x-tenant-slug': 'nolimit'})

    def login(secret):
        return api.post(QA_API + '/auth/login', data={'email': email, 'password': secret})

    started = None
    try:
        assert login(password).status == 200, 'The dedicated lockout account must authenticate before this test.'
        for index in range(attempts):
            if started is None:
                started = time.monotonic()
            response = login('Wrong-QA-' + secrets.token_hex(16))
            if index < attempts - 1:
                assert response.status in (400, 401, 422), 'Lockout occurred before the agreed attempt boundary.'
            else:
                assert response.status == status, 'The configured failed-attempt boundary was not enforced.'
        assert login(password).status == status, 'Correct credentials bypassed an active lockout.'
        if case == 'recovery':
            time.sleep(duration + tolerance)
            assert login(password).status == 200, 'Account did not recover after the agreed lockout period.'
    finally:
        # Even a failed assertion must allow the disposable account's lockout to expire.
        if started is not None:
            time.sleep(max(0, duration + tolerance - (time.monotonic() - started)))
            assert login(password).status == 200, 'Dedicated rate-test account remains locked after cleanup.'
        api.dispose()
