export const browsers = [
  { value: 'chromium', label: 'Chromium' },
  { value: 'chrome', label: 'Google Chrome' },
  { value: 'edge', label: 'Microsoft Edge' },
  { value: 'webkit', label: 'WebKit' },
];

export function browserLabel(value) {
  return browsers.find((browser) => browser.value === value)?.label || 'Chromium';
}
