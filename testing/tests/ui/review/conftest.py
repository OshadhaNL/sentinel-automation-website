"""Isolated, read-only checks added after the live QA coverage review."""
import os
import re
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect

from pages.loginPage import LoginPage


@pytest.fixture(scope='session')
def review_origin(base_url):
    url = urlsplit(base_url)
    return f'{url.scheme}://{url.netloc}'


@pytest.fixture(scope='session')
def review_auth_state(browser, base_url):
    email = os.getenv('TEST_EMAIL')
    password = os.getenv('TEST_PASSWORD')
    assert email and password, 'Set TEST_EMAIL and TEST_PASSWORD for the approved QA account.'
    context = browser.new_context()
    try:
        page = context.new_page()
        login = LoginPage(page)
        login.open(base_url)
        login.login(email, password)
        expect(page).to_have_url(re.compile(r'.*/nolimit/app/home/?$'), timeout=30000)
        # Keep tokens in memory only. Each test receives a separate context.
        return context.storage_state()
    finally:
        context.close()


@pytest.fixture
def readonly_page(browser, review_auth_state):
    context = browser.new_context(storage_state=review_auth_state)
    blocked = []

    def guard(route):
        if route.request.method in ('GET', 'HEAD', 'OPTIONS'):
            route.continue_()
        else:
            blocked.append((route.request.method, urlsplit(route.request.url).path))
            route.abort()

    context.route('**/api/**', guard)
    page = context.new_page()
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(45000)
    try:
        yield page
    finally:
        context.close()
    assert not blocked, f'A read-only check attempted a blocked API write: {blocked}'


@pytest.fixture
def guest_page(browser):
    context = browser.new_context()
    try:
        yield context.new_page()
    finally:
        context.close()
