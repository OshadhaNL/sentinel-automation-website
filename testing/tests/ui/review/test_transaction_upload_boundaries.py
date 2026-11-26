"""Supporting-file validation with upload responses mocked; no file reaches QA storage."""
import re
import base64

import pytest
from playwright.sync_api import expect

from pages.transactionPage import TransactionPage
from pages.uploadSamples import png_bytes


pytestmark = [pytest.mark.ui, pytest.mark.readonly, pytest.mark.boundary]
UPLOAD_LIMIT = 10485760  # Confirmed in the deployed frontend's deferred uploader.


@pytest.fixture
def deferred_upload(readonly_page, review_origin):
    page = readonly_page
    def upload_locally(route):
        if route.request.method != 'POST':
            return route.fallback()
        filename = re.search(br'filename="([^"]+)"', route.request.post_data_buffer or b'')
        assert filename, 'Expected a multipart upload with a filename.'
        name = filename.group(1).decode('utf-8')
        route.fulfill(status=200, json={'success': True, 'message': 'Local upload simulation', 'data': {
            'fileName': name, 'fileType': 'png', 'refId': 'qa-local-file', 'fileKey': 'qa-local-only',
            'tempUrl': 'data:image/png;base64,' + base64.b64encode(png_bytes()).decode(),
        }})
    page.route('**/api/v1/documents/upload', upload_locally)
    page.goto(review_origin + '/nolimit/app/transaction-activities', wait_until='domcontentloaded')
    transaction = TransactionPage(page)
    transaction.open_add_modal()
    return transaction


def uploaded(transaction):
    return transaction.active_modal.locator('.uploaded.show-file .uploaded-file')


@pytest.mark.positive
@pytest.mark.parametrize('size', [None, UPLOAD_LIMIT - 1, UPLOAD_LIMIT], ids=['small-valid', 'limit-minus-one', 'exact-limit'])
def test_boundary_deferred_png_accepts_size_through_inclusive_limit(deferred_upload, size):
    transaction = deferred_upload
    transaction.active_modal.locator('input[type="file"]').last.set_input_files(
        {'name': 'qa-boundary.png', 'mimeType': 'image/png', 'buffer': png_bytes(size)})
    expect(uploaded(transaction).last).to_contain_text('qa-boundary.png', timeout=15000)
    transaction.cancel_modal()


@pytest.mark.negative
def test_boundary_deferred_png_rejects_one_byte_over_limit(deferred_upload):
    transaction = deferred_upload
    transaction.active_modal.locator('input[type="file"]').last.set_input_files(
        {'name': 'qa-oversize.png', 'mimeType': 'image/png', 'buffer': png_bytes(UPLOAD_LIMIT + 1)})
    expect(transaction.page.get_by_text('File is too big! Upload files below 10MB.', exact=True)).to_be_visible()
    expect(uploaded(transaction)).to_have_count(0)


@pytest.mark.negative
@pytest.mark.parametrize('extension', ['txt', 'exe', 'svg', 'gif', 'csv', 'zip', ''])
def test_negative_deferred_uploader_rejects_unsupported_extension(deferred_upload, extension):
    transaction = deferred_upload
    name = 'qa-unsupported' + ('.' + extension if extension else '')
    transaction.active_modal.locator('input[type="file"]').last.set_input_files(
        {'name': name, 'mimeType': 'image/png', 'buffer': png_bytes()})
    expect(transaction.page.get_by_text('Only PDF, PNG, JPG, or JPEG files are supported.', exact=True)).to_be_visible()
    expect(uploaded(transaction)).to_have_count(0)


@pytest.mark.positive
@pytest.mark.parametrize('name', ['qa.PNG', 'qa spaced name.png', 'qa-漢字-é.png', 'qa.multiple.parts.png', 'qa_file-123.png'])
def test_positive_deferred_png_preserves_filename(deferred_upload, name):
    transaction = deferred_upload
    transaction.active_modal.locator('input[type="file"]').last.set_input_files(
        {'name': name, 'mimeType': 'image/png', 'buffer': png_bytes()})
    expect(uploaded(transaction).last).to_contain_text(name, timeout=15000)
    transaction.cancel_modal()


@pytest.mark.positive
def test_positive_cancelled_file_draft_is_not_attached_to_next_transaction(deferred_upload):
    transaction = deferred_upload
    transaction.active_modal.locator('input[type="file"]').last.set_input_files(
        {'name': 'qa-unsaved.png', 'mimeType': 'image/png', 'buffer': png_bytes()})
    expect(uploaded(transaction).last).to_contain_text('qa-unsaved.png', timeout=15000)
    transaction.cancel_modal()
    transaction.open_add_modal()
    expect(uploaded(transaction)).to_have_count(0)
