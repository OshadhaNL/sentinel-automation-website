"""Small helpers for locally simulated failures; no request body is logged."""
import re
import json
from playwright.sync_api import expect


QA_API = 'https://sentinel-austrac-qa-be.northlark.com/api/v1'
FAILURE_MESSAGE = 'Simulated QA request rejection'


def session_headers(page):
    raw = page.evaluate("localStorage.getItem('accessToken:nolimit')")
    assert raw, 'No authenticated session is available.'
    try:
        token = json.loads(raw)
    except json.JSONDecodeError:
        token = raw
    assert isinstance(token, str)
    return {'Authorization': 'Bearer ' + token, 'x-tenant-slug': 'nolimit'}


def expect_failure_notice(page, status):
    if status == 'offline':
        expect(page.locator('.ant-notification-notice, .ant-message-notice').first).to_be_visible(timeout=15000)
    elif status == 429:
        expect(page.locator('.ant-notification-notice, .ant-message-notice').filter(
            has_text=re.compile(r'too many|wait|rate|retry|Simulated QA request rejection', re.I)).first).to_be_visible(timeout=15000)
    else:
        expect(page.get_by_text(FAILURE_MESSAGE, exact=True).first).to_be_visible(timeout=15000)


def reject_request(page, endpoint, status, method):
    calls = []
    pattern = re.compile(r'.*/api/v1/' + re.escape(endpoint) + r'(?:/[^?]*)?(?:\?.*)?$')

    def reject(route):
        if route.request.method != method:
            return route.fallback()
        calls.append(method)
        if status == 'offline':
            route.abort('internetdisconnected')
        else:
            route.fulfill(status=status, json={'message': FAILURE_MESSAGE})

    page.route(pattern, reject)
    return calls
