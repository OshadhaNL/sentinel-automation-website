"""Focused accessibility/reflow regressions; not a full WCAG conformance audit."""
import pytest
from playwright.sync_api import expect

from pages.loginPage import LoginPage


pytestmark = [pytest.mark.ui, pytest.mark.readonly, pytest.mark.positive]
ROUTES = [('home', 'Home'), ('dashboard', 'Dashboard'), ('profiles', 'Profiles'),
          ('transaction-activities', 'Transactions'), ('screening', 'Screening'),
          ('profile-settings', 'Profile Settings')]


@pytest.mark.parametrize('width', [375, 768, 1440], ids=['mobile', 'tablet', 'desktop'])
def test_positive_login_reflows_without_page_overflow(guest_page, base_url, width):
    guest_page.set_viewport_size({'width': width, 'height': 900})
    login = LoginPage(guest_page)
    login.open(base_url)
    for control in (login.email_input, login.password_input, login.login_button):
        expect(control).to_be_in_viewport()
    assert guest_page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Login has page-level horizontal overflow.'


def test_positive_login_supports_keyboard_and_explicit_input_labels(guest_page, base_url):
    login = LoginPage(guest_page)
    login.open(base_url)
    expect(guest_page.get_by_label('Email Address', exact=True)).to_have_count(1)
    expect(guest_page.get_by_label('Password', exact=True)).to_have_count(1)
    login.email_input.focus()
    guest_page.keyboard.press('Tab')
    expect(login.password_input).to_be_focused()
    assert login.password_input.evaluate('(element) => getComputedStyle(element).outlineStyle !== "none" || getComputedStyle(element).boxShadow !== "none"'), 'Focused password field has no visible focus indicator.'


@pytest.mark.parametrize('path,heading', ROUTES)
def test_positive_application_landmarks_language_and_button_names(readonly_page, review_origin, path, heading):
    page = readonly_page
    page.goto(review_origin + '/nolimit/app/' + path, wait_until='domcontentloaded')
    expect(page.locator('main h1')).to_have_count(1)
    expect(page.locator('main h1')).to_be_visible()
    assert page.title().strip(), 'The document has no page title.'
    assert page.locator('html').get_attribute('lang'), 'The document language is missing.'
    # Return only element type/class, never client names or displayed business data.
    unnamed = page.locator('button:visible').evaluate_all('''elements => elements.filter(element => {
        const name = element.getAttribute('aria-label') || element.getAttribute('title') ||
            (element.getAttribute('aria-labelledby') || '').split(/\\s+/).map(id => document.getElementById(id)?.textContent || '').join(' ') ||
            element.innerText || Array.from(element.querySelectorAll('img[alt]')).map(image => image.alt).join(' ') ||
            element.querySelector('svg title')?.textContent || '';
        return !name.replace(/[\\uE000-\\uF8FF]/g, '').trim();
    }).map(element => element.tagName + '.' + element.className)''')
    assert not unnamed, f'Visible buttons need accessible names: {unnamed}'


@pytest.mark.parametrize('path,heading', ROUTES)
@pytest.mark.parametrize('width', [375, 768], ids=['mobile', 'tablet'])
def test_positive_application_reflow_preserves_main_content(readonly_page, review_origin, path, heading, width):
    page = readonly_page
    page.set_viewport_size({'width': width, 'height': 900})
    page.goto(review_origin + '/nolimit/app/' + path, wait_until='domcontentloaded')
    expect(page.locator('main h1')).to_be_in_viewport(timeout=20000)
    # Wide tables may scroll inside their container; the entire page must not.
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'The page overflows horizontally.'


def test_positive_transaction_dialog_exposes_modal_semantics(readonly_page, review_origin):
    from pages.transactionPage import TransactionPage
    readonly_page.goto(review_origin + '/nolimit/app/transaction-activities')
    transaction = TransactionPage(readonly_page)
    transaction.open_add_modal()
    dialog = readonly_page.get_by_role('dialog')
    expect(dialog).to_be_visible()
    expect(dialog).to_have_attribute('aria-modal', 'true')
    assert dialog.get_attribute('aria-label') or dialog.get_attribute('aria-labelledby'), 'Dialog needs an accessible title.'
    assert dialog.evaluate('(element) => element.contains(document.activeElement)'), 'Focus did not move inside the modal.'
    readonly_page.keyboard.press('Escape')
    expect(dialog).to_be_hidden()
