// Frontend fixtures only. These records are not real test executions.
export const modules = [
  { name: 'Login', total: 58, passed: 50, failed: 5, skipped: 1, notExecuted: 2, color: 'var(--chart-1)', icon: 'login' },
  { name: 'Home', total: 42, passed: 37, failed: 3, skipped: 1, notExecuted: 1, color: 'var(--chart-2)', icon: 'home' },
  { name: 'Dashboard', total: 59, passed: 49, failed: 6, skipped: 2, notExecuted: 2, color: 'var(--chart-3)', icon: 'dashboard' },
  { name: 'Onboarding', total: 66, passed: 53, failed: 8, skipped: 3, notExecuted: 2, color: 'var(--chart-4)', icon: 'onboarding' },
  { name: 'Profiles', total: 28, passed: 25, failed: 2, skipped: 0, notExecuted: 1, color: 'var(--chart-5)', icon: 'profiles' },
  { name: 'Transactions', total: 36, passed: 32, failed: 2, skipped: 1, notExecuted: 1, color: 'var(--chart-6)', icon: 'transactions' },
  { name: 'Screening', total: 35, passed: 30, failed: 2, skipped: 2, notExecuted: 1, color: 'var(--chart-7)', icon: 'screening' },
];

export const totals = modules.reduce((summary, module) => {
  for (const key of Object.keys(summary)) summary[key] += module[key];
  return summary;
}, { total: 0, passed: 0, failed: 0, skipped: 0, notExecuted: 0 });

// UTC timestamps are formatted in the viewer's local time.
export const executions = [
  { id: 'RUN-0158', module: 'Login', scope: 'All Tests', executedAt: '2026-11-18T05:15:00Z', result: 'Passed', tester: 'Sample Tester', mode: 'Headless', duration: '2m 34s' },
  { id: 'RUN-0157', module: 'Onboarding', scope: 'Positive', executedAt: '2026-11-17T09:50:00Z', result: 'Failed', tester: 'Sample Tester', mode: 'Headed', duration: '4m 12s' },
  { id: 'RUN-0156', module: 'Dashboard', scope: 'All Tests', executedAt: '2026-11-16T05:40:00Z', result: 'Passed', tester: 'Sample Tester', mode: 'Headless', duration: '3m 08s' },
  { id: 'RUN-0155', module: 'Profiles', scope: 'Negative', executedAt: '2026-11-15T04:00:00Z', result: 'Passed', tester: 'Sample Tester', mode: 'Headless', duration: '1m 46s' },
  { id: 'RUN-0154', module: 'Transactions', scope: 'Positive', executedAt: '2026-11-14T07:35:00Z', result: 'Passed', tester: 'Sample Tester', mode: 'Headless', duration: '2m 18s' },
  { id: 'RUN-0153', module: 'Screening', scope: 'All Tests', executedAt: '2026-11-13T03:30:00Z', result: 'Failed', tester: 'Sample Tester', mode: 'Headed', duration: '3m 52s' },
  { id: 'RUN-0152', module: 'Home', scope: 'All Tests', executedAt: '2026-11-12T08:45:00Z', result: 'Passed', tester: 'Sample Tester', mode: 'Headless', duration: '1m 21s' },
];

export function formatDate(value) {
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
  }).format(new Date(value)).replace('am', 'AM').replace('pm', 'PM');
}
