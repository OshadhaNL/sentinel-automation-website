"""Browser names accepted by the dashboard and their Playwright settings."""

BROWSERS = {
    'chromium': {'label': 'Chromium', 'engine': 'chromium', 'channel': None},
    'chrome': {'label': 'Google Chrome', 'engine': 'chromium', 'channel': 'chrome'},
    'edge': {'label': 'Microsoft Edge', 'engine': 'chromium', 'channel': 'msedge'},
    'webkit': {'label': 'WebKit', 'engine': 'webkit', 'channel': None},
}


def browser_label(browser):
    return BROWSERS[browser]['label']
