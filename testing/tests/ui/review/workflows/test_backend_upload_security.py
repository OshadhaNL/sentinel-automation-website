"""Direct backend validation, bypassing UI checks; clean up only returned new upload IDs."""
import re

import pytest

from pages.reviewRequests import QA_API, session_headers
from pages.uploadSamples import png_bytes


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.document_write, pytest.mark.negative]


@pytest.mark.parametrize('case', ['empty', 'text-as-png', 'png-as-pdf', 'unsupported-text', 'double-extension', 'over-byte-limit'])
def test_negative_backend_rejects_invalid_file_content(workflow_page, review_origin, agreed_rules, case):
    rules = agreed_rules.get('documents', {})
    key = 'backend_maximum_bytes' if case == 'over-byte-limit' else 'backend_rejects_' + case.replace('-', '_')
    if rules.get(key) is None:
        pytest.skip(f'Confirm documents.{key} in WORKFLOW_RULES_FILE.')
    if case != 'over-byte-limit':
        assert rules[key] is True, 'This negative case requires a documented rejection policy.'
    page = workflow_page('UPLOAD_SECURITY', deletes=True)
    page.goto(review_origin + '/nolimit/app/home', wait_until='domcontentloaded')
    headers = session_headers(page)
    created = []

    def upload(name, mime, content):
        response = page.context.request.post(QA_API + '/documents/upload', headers=headers,
            multipart={'file': {'name': name, 'mimeType': mime, 'buffer': content}})
        if 200 <= response.status < 300:
            data = response.json().get('data') or {}
            identifier = data.get('refId') or data.get('_id')
            assert isinstance(identifier, str) and re.fullmatch(r'[A-Za-z0-9_-]+', identifier), 'Uploaded object needs a returned ID for cleanup.'
            created.append(identifier)
        return response

    try:
        # Prove the same endpoint accepts a valid control, so a missing form field
        # or unrelated authorization failure cannot masquerade as file validation.
        control = upload('qa-valid-control.png', 'image/png', png_bytes())
        assert 200 <= control.status < 300, 'The valid control upload failed; backend validation is not verified.'
        inputs = {
            'empty': ('qa-empty.png', 'image/png', b''),
            'text-as-png': ('qa-text.png', 'image/png', b'Harmless QA text, not PNG data.'),
            'png-as-pdf': ('qa-mismatch.pdf', 'application/pdf', png_bytes()),
            'unsupported-text': ('qa-unsupported.txt', 'text/plain', b'Harmless QA text.'),
            'double-extension': ('qa-double.png.txt', 'image/png', png_bytes()),
        }
        if case == 'over-byte-limit':
            limit = rules[key]
            assert isinstance(limit, int) and 100 <= limit <= 20 * 1024 * 1024
            values = ('qa-oversize.png', 'image/png', png_bytes(limit + 1))
        else:
            values = inputs[case]
        result = upload(*values)
        assert result.status in (400, 413, 415, 422), 'Backend admitted a file that violates the approved validation policy.'
    finally:
        if created:
            deleted = page.context.request.delete(QA_API + '/documents/delete', headers=headers, data={'ids': created})
            assert deleted.status in (200, 204), 'Cleanup failed for an upload created by this test.'
