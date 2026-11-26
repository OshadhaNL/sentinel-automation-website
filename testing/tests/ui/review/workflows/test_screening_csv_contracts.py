"""Real bulk validation/accounting with a supplied CSV contract and explicit provider budget."""
import csv
import io
import os
from pathlib import Path
import time
from urllib.parse import quote
from uuid import uuid4

import pytest

from pages.reviewRequests import QA_API, session_headers


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.workflow_write, pytest.mark.screening_write]


@pytest.mark.parametrize('case', [
    pytest.param('valid', marks=pytest.mark.positive),
    pytest.param('missing-header', marks=pytest.mark.negative),
    pytest.param('empty', marks=pytest.mark.negative),
    pytest.param('row-limit', marks=pytest.mark.positive),
    pytest.param('row-limit-plus-one', marks=pytest.mark.negative),
    pytest.param('duplicate-row', marks=pytest.mark.negative),
    pytest.param('partial-invalid', marks=pytest.mark.negative),
])
def test_screening_csv_validation_and_final_row_accounting(workflow_page, review_origin, agreed_rules, case):
    rules = agreed_rules.get('screening_csv', {})
    for key in ('file_field', 'batch_name_field', 'name_column', 'required_headers', 'maximum_rows',
                'duplicate_rows', 'partial_failure', 'summary_id_field', 'summary_url_template',
                'accepted_count_field', 'failed_count_field', 'skipped_count_field'):
        if rules.get(key) is None:
            pytest.skip(f'Confirm screening_csv.{key} in WORKFLOW_RULES_FILE.')
    filename = os.getenv('WORKFLOW_SCREENING_CSV_SAMPLE', '')
    assert filename and Path(filename).is_file(), 'Supply an approved, valid CSV sample without production identities.'
    with Path(filename).open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        headers = reader.fieldnames
        sample = next(reader, None)
    assert sample and headers and set(rules['required_headers']).issubset(headers)
    assert rules['name_column'] in headers and rules['required_headers']
    maximum = int(rules['maximum_rows'])
    assert maximum >= 1 and rules['duplicate_rows'] in ('reject-batch', 'skip-duplicates', 'process-all')
    assert rules['partial_failure'] in ('reject-batch', 'process-valid')
    count = maximum if case == 'row-limit' else maximum + 1 if case == 'row-limit-plus-one' else 2 if case in ('duplicate-row', 'partial-invalid') else 1
    budget = int(os.getenv('WORKFLOW_BULK_ROW_BUDGET', '0'))
    if budget < count:
        pytest.skip(f'This case needs explicit WORKFLOW_BULK_ROW_BUDGET >= {count}; provider requests may be charged.')
    page = workflow_page('SCREENING_BULK')
    page.goto(review_origin + '/nolimit/app/home', wait_until='domcontentloaded')
    auth = session_headers(page)
    batch_name = 'QA Bulk ' + uuid4().hex[:12]
    rows = [dict(sample) for _ in range(count)]
    for index, row in enumerate(rows):
        # Distinct synthetic names keep the row-limit test independent of duplicate policy.
        suffix = str(index).translate(str.maketrans('0123456789', 'abcdefghij'))
        row[rules['name_column']] = batch_name + ' ' + suffix
    accepted, failed, skipped = count, 0, 0
    rejected = case in ('missing-header', 'empty', 'row-limit-plus-one')
    if case == 'missing-header':
        headers = [name for name in headers if name != rules['required_headers'][0]]
    elif case == 'duplicate-row':
        rows[1] = dict(rows[0])
        rejected = rules['duplicate_rows'] == 'reject-batch'
        if rules['duplicate_rows'] == 'skip-duplicates':
            accepted, skipped = 1, 1
    elif case == 'partial-invalid':
        rows[1][rules['name_column']] = ''
        rejected = rules['partial_failure'] == 'reject-batch'
        accepted, failed = 1, 1
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=headers, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    payload = b'' if case == 'empty' else content.getvalue().encode('utf-8')
    response = page.context.request.post(QA_API + '/world-check/bulk-search', headers=auth, multipart={
        rules['file_field']: {'name': batch_name + '.csv', 'mimeType': 'text/csv', 'buffer': payload},
        rules['batch_name_field']: batch_name,
    })
    if rejected:
        assert response.status in (400, 413, 422), 'Invalid bulk input was admitted.'
        return
    assert response.status in (200, 201, 202)
    created = response.json().get('data') or {}
    batch_id = created.get(rules['summary_id_field'])
    assert isinstance(batch_id, str) and batch_id
    template = rules['summary_url_template']
    assert template.startswith('/world-check/') and '{id}' in template
    summary_url = QA_API + template.replace('{id}', quote(batch_id, safe=''))
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        result = page.context.request.get(summary_url, headers=auth)
        assert result.status == 200
        data = result.json().get('data') or {}
        counts = tuple(data.get(rules[key]) for key in ('accepted_count_field', 'failed_count_field', 'skipped_count_field'))
        if all(isinstance(value, int) for value in counts) and sum(counts) == count:
            assert counts == (accepted, failed, skipped)
            return
        time.sleep(1)
    raise AssertionError('Bulk job did not account for every submitted row within 90 seconds.')
