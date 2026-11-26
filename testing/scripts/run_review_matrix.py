"""Run the read-only review in installed browsers; keep raw output in ignored reports."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
BROWSERS = {'chromium': ('chromium', None), 'chrome': ('chromium', 'chrome'),
            'edge': ('chromium', 'msedge'), 'webkit': ('webkit', None)}


def run_browser(name, workers):
    engine, channel = BROWSERS[name]
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    target = reports / f'gap-matrix-{name}.xml'
    target.unlink(missing_ok=True)
    with sync_playwright() as playwright:
        options = {'channel': channel} if channel else {}
        try:
            browser = getattr(playwright, engine).launch(**options)
            context = browser.new_context(permissions=['camera'])
            context.close()
            browser.close()
        except Exception as error:
            print(f'{name}: browser unavailable ({type(error).__name__})', flush=True)
            return [dict(browser=name, test='Browser startup', result='Unavailable')]
    command = [sys.executable, '-m', 'pytest', 'tests/ui/review', '-m', 'readonly',
               '--browser', engine, '-n', str(workers), '--dist', 'loadfile', '-q',
               '--tb=line', '--strict-markers', '--junitxml', str(target)]
    if channel:
        command.extend(['--browser-channel', channel])
    environment = os.environ.copy()
    # This runner is deliberately read-only, even in an opted-in parent shell.
    for key in ['WORKFLOW_ALLOW_WRITES', 'WORKFLOW_ALLOW_EMAILS', 'WORKFLOW_SESSION_SECURITY',
                'WORKFLOW_ISOLATED_TENANT_CONFIRMED']:
        environment[key] = '0'
    print(f'{name}: running read-only review', flush=True)
    with (reports / f'gap-matrix-{name}.log').open('w', encoding='utf-8') as output:
        completed = subprocess.run(command, cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT)
    rows = []
    if target.exists():
        for case in ET.parse(target).iter('testcase'):
            result = 'Passed'
            if case.find('failure') is not None or case.find('error') is not None:
                result = 'Failed'
            elif case.find('skipped') is not None:
                result = 'Skipped'
            rows.append(dict(browser=name, test=case.get('classname') + '::' + case.get('name'), result=result))
    if not rows:
        rows.append(dict(browser=name, test='Test collection/process', result=f'Error ({completed.returncode})'))
    elif completed.returncode not in (0, 1):
        rows.append(dict(browser=name, test='Test process did not complete', result=f'Error ({completed.returncode})'))
    print(f"{name}: " + ', '.join(f'{sum(row["result"] == state for row in rows)} {state.lower()}'
                                   for state in ('Passed', 'Failed', 'Skipped')), flush=True)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browsers', nargs='+', choices=BROWSERS, default=list(BROWSERS))
    parser.add_argument('--jobs', type=int, choices=(1, 2, 3), default=1)
    parser.add_argument('--workers', type=int, choices=(0, 1, 2), default=2)
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda name: run_browser(name, args.workers), args.browsers))
    rows = [row for group in results for row in group]
    target = ROOT / 'coverage/browser_matrix_results.csv'
    with target.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=['browser', 'test', 'result'])
        writer.writeheader()
        writer.writerows(rows)
    return int(any(row['result'] not in ('Passed', 'Skipped') for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
