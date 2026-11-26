"""Ownership checks use exact, approved records and two separately supplied accounts."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect

from pages.loginPage import LoginPage
from pages.reviewRequests import QA_API, session_headers


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('kind', ['individual', 'entity', 'transaction', 'document'])
def test_negative_other_client_cannot_read_owned_resource(browser, base_url, kind):
    filename = os.getenv('WORKFLOW_OWNERSHIP_FILE', '').strip()
    if not filename:
        pytest.skip('Set WORKFLOW_OWNERSHIP_FILE with approved resource URLs and account prefixes.')
    check = json.loads(Path(filename).read_text(encoding='utf-8')).get(kind)
    assert check, f'Missing approved ownership case: {kind}'
    url = check['url']
    assert url.startswith(QA_API + '/') and urlsplit(url).hostname == urlsplit(QA_API).hostname
    assert check['denied_status'] in (403, 404)
    assert check['owner'] != check['other'], 'Use two distinct role-account prefixes.'
    contexts = []
    try:
        responses = []
        for prefix in (check['owner'], check['other']):
            email = os.getenv('WORKFLOW_' + prefix + '_EMAIL')
            password = os.getenv('WORKFLOW_' + prefix + '_PASSWORD')
            if not email or not password:
                pytest.skip(f'Supply WORKFLOW_{prefix}_EMAIL and WORKFLOW_{prefix}_PASSWORD.')
            context = browser.new_context()
            contexts.append(context)
            page = context.new_page()
            login = LoginPage(page)
            login.open(base_url)
            login.login(email, password)
            expect(page.get_by_role('heading', name='Welcome', exact=True)).to_be_visible(timeout=30000)
            responses.append(context.request.get(url, headers=session_headers(page), max_redirects=0))
        assert responses[0].status == 200, 'The owning test account cannot read its own fixture.'
        assert responses[1].status == check['denied_status'], 'Another client account could read the owned resource.'
        assert not responses[1].json().get('data'), 'Denied ownership response exposed resource data.'
    finally:
        for context in contexts:
            context.close()
