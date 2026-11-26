"""Own-file lifecycle and exact upload-size boundaries on an empty disposable slot."""
import os
import re
from urllib.parse import quote
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from pages.profiles.individual.individualDocumentsPage import IndividualDocumentsPage
from pages.uploadSamples import png_bytes, pdf_bytes


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.document_write]


def make_png(path, size=None):
    path.write_bytes(png_bytes(size))
    return path


@pytest.fixture
def document_slot(workflow_page, review_origin):
    page = workflow_page('DOCUMENTS', deletes=True)
    client_id = os.getenv('WORKFLOW_DOCUMENT_CLIENT_ID', '').strip()
    assert re.fullmatch(r'SENTINEL[A-Za-z0-9]+', client_id), 'Set WORKFLOW_DOCUMENT_CLIENT_ID to a disposable individual profile.'
    page.goto(review_origin + '/nolimit/app/profiles/individual/process?step=documents&client=' + quote(client_id), wait_until='domcontentloaded')
    profile = IndividualDocumentsPage(page)
    expect(profile.heading).to_be_visible()
    profile.open_documents_upload()
    expect(profile.document_reference()).to_contain_text(client_id)
    # Do not mistake an uploader's initial empty render for an empty saved slot.
    page.wait_for_load_state('networkidle', timeout=30000)
    # Never replace an existing document, even on a disposable client.
    slot = os.getenv('WORKFLOW_DOCUMENT_SLOT', 'Others')
    assert slot in profile.DOCUMENT_TYPES
    expect(profile.document_uploader(slot)).to_be_visible()
    expect(profile.document_uploader(slot).locator('.uploaded.show-file')).to_have_count(0)
    return profile, slot


def own_file(profile, slot, filename):
    return profile.document_uploader(slot).locator('.uploaded.show-file').filter(
        has=profile.page.get_by_text(filename, exact=True))


def delete_own_file(profile, slot, filename):
    if not own_file(profile, slot, filename).count():
        return
    modal = profile.delete_document(slot)
    modal.locator('button.modal-z-primary-btn').click()
    expect(modal).to_be_hidden()
    expect(own_file(profile, slot, filename)).to_have_count(0)


def cleanup_own_file(profile, slot, filename):
    # Reload also closes an interrupted preview/delete dialog before cleanup.
    profile.page.reload(wait_until='domcontentloaded')
    profile.open_documents_upload()
    profile.page.wait_for_load_state('networkidle', timeout=30000)
    delete_own_file(profile, slot, filename)


@pytest.mark.positive
def test_positive_upload_preview_cancel_delete_reload_then_delete(document_slot, tmp_path):
    profile, slot = document_slot
    path = make_png(tmp_path / ('qa-workflow-' + uuid4().hex[:12] + '.png'))
    try:
        profile.upload_document(slot, str(path))
        expect(own_file(profile, slot, path.name)).to_be_visible(timeout=30000)
        profile.page.reload(wait_until='domcontentloaded')
        profile.open_documents_upload()
        expect(own_file(profile, slot, path.name)).to_be_visible()
        preview = profile.open_document_preview(slot)
        preview.locator('button.modal-z-close').first.click()
        expect(preview).to_be_hidden()
        modal = profile.delete_document(slot)
        modal.locator('button.modal-z-secondary-btn').click()
        expect(modal).to_be_hidden()
        profile.page.reload(wait_until='domcontentloaded')
        profile.open_documents_upload()
        expect(own_file(profile, slot, path.name)).to_be_visible()
        delete_own_file(profile, slot, path.name)
        profile.page.reload(wait_until='domcontentloaded')
        profile.open_documents_upload()
        expect(own_file(profile, slot, path.name)).to_have_count(0)
    finally:
        cleanup_own_file(profile, slot, path.name)


@pytest.mark.boundary
@pytest.mark.parametrize('offset', [
    pytest.param(-1, id='limit-minus-one', marks=pytest.mark.positive),
    pytest.param(0, id='exact-limit', marks=pytest.mark.positive),
    pytest.param(1, id='limit-plus-one', marks=pytest.mark.negative),
])
def test_boundary_document_size_acceptance_matches_displayed_limit(document_slot, tmp_path, offset):
    profile, slot = document_slot
    # Confirmed in the deployed frontend uploader (26 November 2026).
    limit = 10485760
    expect(profile.document_uploader(slot)).to_contain_text(re.compile(r'10\s*MB', re.I))
    path = make_png(tmp_path / ('qa-size-' + uuid4().hex[:12] + '.png'), limit + offset)
    try:
        profile.upload_document(slot, str(path))
        if offset <= 0:
            expect(own_file(profile, slot, path.name)).to_be_visible(timeout=30000)
        else:
            expect(profile.page.locator('.ant-notification-notice, .ant-message-notice').filter(
                has_text=re.compile(r'size|large|10\s*MB', re.I)).first).to_be_visible()
        profile.page.reload(wait_until='domcontentloaded')
        profile.open_documents_upload()
        if offset <= 0:
            expect(own_file(profile, slot, path.name)).to_be_visible()
        else:
            expect(own_file(profile, slot, path.name)).to_have_count(0)
    finally:
        cleanup_own_file(profile, slot, path.name)


@pytest.mark.negative
@pytest.mark.parametrize('case', ['png-as-pdf', 'pdf-as-png'])
def test_negative_content_extension_mismatch_matches_document_policy(document_slot, agreed_rules, tmp_path, case):
    profile, slot = document_slot
    allowed = agreed_rules.get('documents', {}).get('mime_mismatch_allowed')
    if allowed is None:
        pytest.skip('Confirm documents.mime_mismatch_allowed in WORKFLOW_RULES_FILE.')
    assert isinstance(allowed, bool)
    path = tmp_path / ('qa-content-' + uuid4().hex[:12] + ('.pdf' if case == 'png-as-pdf' else '.png'))
    path.write_bytes(png_bytes() if case == 'png-as-pdf' else pdf_bytes())
    try:
        profile.upload_document(slot, str(path))
        if allowed:
            expect(own_file(profile, slot, path.name)).to_be_visible(timeout=30000)
        else:
            expect(profile.page.locator('.ant-notification-notice-error, .ant-message-error').first).to_be_visible()
        profile.page.reload(wait_until='domcontentloaded')
        profile.open_documents_upload()
        if allowed:
            expect(own_file(profile, slot, path.name)).to_be_visible()
        else:
            expect(own_file(profile, slot, path.name)).to_have_count(0)
    finally:
        cleanup_own_file(profile, slot, path.name)


def test_negative_duplicate_filename_does_not_silently_replace_another_slot(document_slot, agreed_rules, tmp_path):
    profile, first_slot = document_slot
    policy = agreed_rules.get('documents', {}).get('duplicate_filename')
    if policy is None:
        pytest.skip('Confirm documents.duplicate_filename in WORKFLOW_RULES_FILE.')
    assert policy in ('reject', 'allow-independent')
    empty = [slot for slot in profile.DOCUMENT_TYPES if slot != first_slot and not profile.document_has_uploaded_file(slot)]
    assert empty, 'This workflow requires two empty document slots on the disposable client.'
    second_slot = empty[0]
    path = make_png(tmp_path / ('qa-duplicate-' + uuid4().hex[:12] + '.png'))
    try:
        profile.upload_document(first_slot, str(path))
        expect(own_file(profile, first_slot, path.name)).to_be_visible(timeout=30000)
        profile.upload_document(second_slot, str(path))
        if policy == 'reject':
            expect(profile.page.locator('.ant-notification-notice-error').first).to_be_visible()
        else:
            expect(own_file(profile, second_slot, path.name)).to_be_visible(timeout=30000)
        profile.page.reload(wait_until='domcontentloaded')
        profile.open_documents_upload()
        expect(own_file(profile, first_slot, path.name)).to_be_visible()
        if policy == 'reject':
            expect(own_file(profile, second_slot, path.name)).to_have_count(0)
        else:
            expect(own_file(profile, second_slot, path.name)).to_be_visible()
    finally:
        cleanup_own_file(profile, first_slot, path.name)
        cleanup_own_file(profile, second_slot, path.name)


@pytest.mark.negative
@pytest.mark.parametrize('failure', [500, 'offline'])
def test_negative_failed_replacement_keeps_original_saved_document(document_slot, tmp_path, failure):
    profile, slot = document_slot
    page = profile.page
    original = make_png(tmp_path / ('qa-original-' + uuid4().hex[:12] + '.png'))
    replacement = make_png(tmp_path / ('qa-replacement-' + uuid4().hex[:12] + '.png'))
    calls = []

    def reject(route):
        # Includes object-storage PUTs as well as API writes.
        if route.request.method in ('POST', 'PUT', 'PATCH'):
            calls.append(route.request.method)
            if failure == 'offline':
                route.abort('internetdisconnected')
            else:
                route.fulfill(status=500, json={'message': 'Simulated replacement failure'})
        else:
            route.fallback()

    try:
        profile.upload_document(slot, str(original))
        expect(own_file(profile, slot, original.name)).to_be_visible(timeout=30000)
        page.route('**/*', reject)
        profile.upload_document(slot, str(replacement))
        expect(page.locator('.ant-notification-notice-error').first).to_be_visible()
        assert calls, 'No replacement request exercised the simulated failure.'
        page.unroute('**/*', reject)
        page.reload(wait_until='domcontentloaded')
        profile.open_documents_upload()
        expect(own_file(profile, slot, original.name)).to_be_visible()
        expect(own_file(profile, slot, replacement.name)).to_have_count(0)
    finally:
        page.unroute('**/*', reject)
        cleanup_own_file(profile, slot, original.name)
        cleanup_own_file(profile, slot, replacement.name)
