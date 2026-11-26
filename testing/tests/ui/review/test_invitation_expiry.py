"""Read-only checks for supplied expired/used links; do not open active links that may send OTPs."""
import os
import re
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly, pytest.mark.negative]


@pytest.mark.parametrize('case', ['EXPIRED', 'USED'])
def test_negative_unusable_invitation_does_not_grant_app_access(guest_page, review_origin, case):
    link = os.getenv('WORKFLOW_' + case + '_INVITE_URL', '').strip()
    if not link:
        pytest.skip(f'Provide WORKFLOW_{case}_INVITE_URL for an approved unusable invitation.')
    assert urlsplit(link).netloc == urlsplit(review_origin).netloc and link.startswith(review_origin + '/nolimit/')
    # Failed-link inspection cannot send OTPs or redeem the supplied invitation.
    writes = []
    def guard(route):
        if route.request.method in ('GET', 'HEAD', 'OPTIONS'):
            route.continue_()
        else:
            writes.append(route.request.method)
            route.abort()
    guest_page.route('**/api/**', guard)
    guest_page.goto(link, wait_until='domcontentloaded')
    expect(guest_page.get_by_text(re.compile(r'expired|invalid|no longer valid|already used', re.I)).first).to_be_visible(timeout=20000)
    guest_page.goto(review_origin + '/nolimit/app/home', wait_until='domcontentloaded')
    expect(guest_page).to_have_url(re.compile(r'.*/nolimit/login/?$'))
    assert not writes, 'An unusable invitation attempted a mutating request.'
