"""Create/delete only fresh test identities. Real emails require a separate explicit opt-in."""
import os
import re
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from pages.reviewRequests import QA_API, session_headers
from pages.reviewMailbox import wait_for_invitation
from pages.settingsPage import SettingsPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write]


def mail_recipient():
    if os.getenv('WORKFLOW_ALLOW_EMAILS') != '1':
        pytest.skip('Account/invitation creation may send mail; set WORKFLOW_ALLOW_EMAILS=1 only with an approved test inbox.')
    domain = os.getenv('WORKFLOW_TEST_EMAIL_DOMAIN', '').strip()
    assert re.fullmatch(r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}', domain), 'Provide a controlled WORKFLOW_TEST_EMAIL_DOMAIN.'
    return 'qa.' + uuid4().hex[:16] + '@' + domain


def created_id(response):
    assert 200 <= response.status < 300
    data = response.json().get('data') or {}
    record = data.get('user', data)
    identifier = record.get('refId') or record.get('_id')
    assert isinstance(identifier, str) and re.fullmatch(r'[A-Za-z0-9_-]+', identifier), 'Creation response needs a stable identity for safe cleanup.'
    return identifier


@pytest.mark.parametrize('case', ['read-back', 'duplicate-email', 'disable-and-reactivate'])
def test_positive_disposable_staff_account_lifecycle(workflow_page, review_origin, case):
    recipient = mail_recipient()
    page = workflow_page('ACCOUNTS', deletes=True)
    settings = SettingsPage(page, review_origin)
    settings.open_add_user()
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill('QA Disposable')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill('Lifecycle')
    settings.modal.get_by_placeholder('Enter email address', exact=True).fill(recipient)
    settings.modal.locator('.ant-select-selector').first.click()
    page.locator('.ant-select-dropdown:visible .ant-select-item-option').filter(has_text='Client').first.click()
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill('QA Disposable')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill('Lifecycle')
    settings.modal.get_by_placeholder('Enter email address', exact=True).fill(recipient)
    identifier = None
    headers = session_headers(page)
    try:
        with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/user-management')) as pending:
            settings.modal.get_by_role('button', name='Add User', exact=True).click()
        identifier = created_id(pending.value)
        expect(settings.modal).to_have_count(0)
        saved = page.context.request.get(QA_API + '/user-management/' + identifier, headers=headers)
        assert saved.status == 200 and saved.json()['data']['email'] == recipient
        if case == 'duplicate-email':
            payload = pending.value.request.post_data_json
            duplicate = page.context.request.post(QA_API + '/user-management', headers=headers, data=payload)
            assert duplicate.status in (400, 409, 422), 'Duplicate email was accepted.'
        elif case == 'disable-and-reactivate':
            for status in ('inactive', 'active'):
                changed = page.context.request.put(QA_API + '/user-management/status/' + identifier, headers=headers, data={'status': status})
                assert 200 <= changed.status < 300
                current = page.context.request.get(QA_API + '/user-management/' + identifier, headers=headers)
                assert current.status == 200 and current.json()['data']['status'] == status
    finally:
        if identifier:
            deleted = page.context.request.delete(QA_API + '/user-management/' + identifier, headers=headers)
            assert deleted.status in (200, 204)
            assert page.context.request.get(QA_API + '/user-management/' + identifier, headers=headers).status in (400, 404)


@pytest.mark.parametrize('case', ['create-delete', 'email-delivery', 'reset-link'])
def test_positive_disposable_invitation_link_and_email(workflow_page, review_origin, case):
    recipient = mail_recipient()
    if case == 'email-delivery':
        assert os.getenv('WORKFLOW_IMAP_HOST') and os.getenv('WORKFLOW_IMAP_USER'), 'Configure the test inbox before creating an invitation.'
        assert os.getenv('WORKFLOW_IMAP_OAUTH_TOKEN') or os.getenv('WORKFLOW_IMAP_PASSWORD')
    page = workflow_page('INVITATIONS', deletes=True)
    settings = SettingsPage(page, review_origin)
    settings.open_invite_form()
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill('QA Disposable')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill('Invitation')
    settings.modal.get_by_placeholder('Enter email address', exact=True).fill(recipient)
    settings.modal.locator('.ant-select-selector').first.click()
    page.locator('.ant-select-dropdown:visible .ant-select-item-option').filter(has_text='Seller').first.click()
    # The role-dependent form schema can reset fields during its render.
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    settings.modal.get_by_placeholder('Enter first name', exact=True).fill('QA Disposable')
    settings.modal.get_by_placeholder('Enter last name', exact=True).fill('Invitation')
    settings.modal.get_by_placeholder('Enter email address', exact=True).fill(recipient)
    headers = session_headers(page)
    identifier = None
    try:
        with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/user-management/invite')) as pending:
            settings.modal.get_by_role('button', name='Send Invite', exact=True).click()
        identifier = created_id(pending.value)
        response = page.context.request.get(QA_API + '/user-management/invite/link/' + identifier, headers=headers)
        assert response.status == 200
        data = response.json().get('data')
        link = data if isinstance(data, str) else data.get('link') or data.get('inviteLink') or data.get('url')
        assert isinstance(link, str) and link.startswith(review_origin + '/nolimit/')
        if case == 'email-delivery':
            wait_for_invitation(recipient, link)
        elif case == 'reset-link':
            old_token = parse_qs(urlsplit(link).query).get('token', [None])[0]
            assert old_token, 'The generated invitation must contain a verifiable token.'
            reset = page.context.request.put(QA_API + '/user-management/invite/reset/' + identifier, headers=headers)
            assert 200 <= reset.status < 300
            replacement = page.context.request.get(QA_API + '/user-management/invite/link/' + identifier, headers=headers)
            assert replacement.status == 200
            new_data = replacement.json()['data']
            new_link = new_data if isinstance(new_data, str) else new_data.get('link') or new_data.get('inviteLink') or new_data.get('url')
            assert new_link and new_link != link, 'Reset did not rotate the invitation link.'
            new_token = parse_qs(urlsplit(new_link).query).get('token', [None])[0]
            assert new_token and new_token != old_token
            for token, valid in ((old_token, False), (new_token, True)):
                verified = page.context.request.get(QA_API + '/auth/temp-login/verify',
                    headers={'x-tenant-slug': 'nolimit'}, params={'token': token}, max_redirects=0)
                assert verified.status in ((200,) if valid else (400, 401, 403, 404, 410, 422)), 'Invitation reset did not enforce token validity.'
    finally:
        if identifier:
            deleted = page.context.request.delete(QA_API + '/user-management/invite/' + identifier, headers=headers)
            assert deleted.status in (200, 204)
