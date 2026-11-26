"""Camera failures on an explicitly supplied unverified test client; no real camera or uploads."""
import os
import re
from urllib.parse import quote

import pytest
from playwright.sync_api import expect

from pages.individualOnboardingPage import IndividualOnboardingPage


pytestmark = [pytest.mark.ui, pytest.mark.workflow, pytest.mark.readonly]


@pytest.fixture
def camera_client(request, browser_name, review_origin):
    client = os.getenv('WORKFLOW_CAMERA_CLIENT_ID', '').strip()
    if not client:
        pytest.skip('Set WORKFLOW_CAMERA_CLIENT_ID to an approved unverified individual test client.')
    assert re.fullmatch(r'SENTINEL[A-Za-z0-9]+', client)
    readonly_page = request.getfixturevalue('readonly_page')
    return readonly_page, review_origin + '/nolimit/app/onboarding/individual/process?step=verification&client=' + quote(client)


@pytest.mark.negative
@pytest.mark.parametrize('error', ['NotAllowedError', 'NotFoundError', 'NotReadableError'])
def test_negative_camera_failure_can_retry_and_close_without_upload(camera_client, error):
    page, url = camera_client
    page.add_init_script("""(() => {
        window.__qaMediaRequests = 0;
        navigator.mediaDevices.getUserMedia = () => {
            window.__qaMediaRequests++;
            return Promise.reject(new DOMException('Simulated camera failure', %s));
        };
    })();""" % repr(error))
    page.goto(url, wait_until='domcontentloaded')
    individual = IndividualOnboardingPage(page)
    individual.verify_page_loaded()
    individual.open_camera_warning()
    individual.accept_camera_warning()
    denied = page.locator('.webcam-card .webcam-denied').filter(has=page.locator('i.fa-webcam-slash'))
    expect(denied).to_be_visible()
    expect(page.locator('.webcam-card .take-photo-btn')).to_have_count(0)
    denied.get_by_role('button', name='Try Again', exact=True).click()
    expect(denied).to_be_visible()
    page.wait_for_function('window.__qaMediaRequests >= 2')
    page.locator('.webcam-card:visible button.close-btn').first.click()
    expect(page.locator('.webcam-card:visible')).to_have_count(0)


@pytest.mark.positive
def test_positive_closing_simulated_camera_stops_every_video_track(camera_client):
    page, url = camera_client
    page.add_init_script("""(() => {
        window.__qaStreams = [];
        navigator.mediaDevices.getUserMedia = async () => {
            const canvas = document.createElement('canvas');
            canvas.width = canvas.height = 64;
            canvas.getContext('2d').fillRect(0, 0, 64, 64);
            const stream = canvas.captureStream(5);
            window.__qaStreams.push(stream);
            return stream;
        };
    })();""")
    page.goto(url, wait_until='domcontentloaded')
    individual = IndividualOnboardingPage(page)
    individual.verify_page_loaded()
    individual.open_live_camera()
    page.wait_for_function('window.__qaStreams.length === 1')
    individual.close_live_camera()
    page.wait_for_function("window.__qaStreams.every(s => s.getTracks().every(t => t.readyState === 'ended'))")
