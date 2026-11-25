import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import uuid
import logging

from fastapi import HTTPException
from sqlalchemy import select, update

from app.db.database import utcnow
from app.models import RunnerLock, TestCase, TestResult, TestRun
from app.services.discovery import collect_tests, sync_inventory, bridge_environment, pytest_command, check_workers
from app.services.reports import generate_reports
from app.services.selection import selected_cases
from app.services.browsers import BROWSERS, browser_label

ACTIVE = ('Pending', 'Running')
logger = logging.getLogger(__name__)


def phase_result(previous, event):
    status = previous
    if event['outcome'] == 'failed':
        status = 'Failed' if event['phase'] == 'call' else 'Error'
    elif event['outcome'] == 'skipped' and previous not in ('Failed', 'Error'):
        status = 'Skipped'
    elif event['phase'] == 'call' and event['outcome'] == 'passed' and previous not in ('Error', 'Skipped'):
        status = 'Passed'
    return status


class Runner:
    def __init__(self, sessions, settings):
        self.sessions = sessions
        self.settings = settings
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = None

    def acquire(self):
        if not self.lock.acquire(blocking=False):
            raise HTTPException(409, 'Another execution or discovery is in progress. Requests are not queued.')
        try:
            with self.sessions() as db:
                changed = db.execute(update(RunnerLock).where(RunnerLock.id == 1, RunnerLock.owner.is_(None)).values(owner=str(uuid.uuid4())))
                db.commit()
                if not changed.rowcount:
                    raise HTTPException(409, 'Another execution is in progress.')
        except Exception:
            self.lock.release()
            raise

    def release(self):
        try:
            with self.sessions() as db:
                db.execute(update(RunnerLock).where(RunnerLock.id == 1).values(owner=None))
                db.commit()
        finally:
            self.lock.release()

    def synchronize(self):
        self.acquire()
        try:
            records, warnings = collect_tests(self.settings)
            with self.sessions() as db:
                info = sync_inventory(db, records, warnings, self.settings.executor == 'mock')
                return dict(count=info.count, warnings=info.warnings, isMock=self.settings.executor == 'mock')
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            raise HTTPException(422, str(error)) from error
        finally:
            self.release()

    def start(self, user, options):
        self.acquire()
        try:
            check_workers(self.settings, options.workers)
            records, warnings = collect_tests(self.settings)
            with self.sessions() as db:
                sync_inventory(db, records, warnings, self.settings.executor == 'mock')
                cases = selected_cases(db, self.settings, options)
                if self.settings.executor == 'pytest' and any(case.requires_real_camera or not case.camera_classified for case in cases) and not self.settings.camera_available:
                    raise ValueError('Real camera availability is not confirmed. Configure REAL_CAMERA_AVAILABLE only on a suitable execution machine/session.')
                # Each browser gets a normal run, preserving the existing history model.
                batch_id = str(uuid.uuid4()) if len(options.browsers) > 1 else None
                run_ids = []
                for browser in options.browsers:
                    run = TestRun(executed_by_user_id=user.id, scope_type=options.scope_type, scope_value=options.scope_value,
                                  selection=options.selection, browser_mode=options.browser_mode, camera_mode=options.camera_mode,
                                  workers=options.workers, browser=browser, batch_id=batch_id,
                                  is_mock=self.settings.executor == 'mock')
                    db.add(run)
                    db.flush()
                    for case in cases:
                        db.add(TestResult(test_run_id=run.id, test_case_id=case.id))
                    run_ids.append(run.id)
                db.commit()
                run_id = run_ids[0]
            self.thread = threading.Thread(target=self.execute, args=(run_id,), daemon=True)
            self.thread.start()
            return run_id
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            self.release()
            raise HTTPException(422, str(error)) from error
        except Exception:
            self.release()
            raise

    def save_result(self, run_id, case_id, status, duration=0, message=None):
        with self.sessions() as db:
            result = db.scalar(select(TestResult).where(TestResult.test_run_id == run_id, TestResult.test_case_id == case_id))
            result.status = status
            result.duration_seconds = duration
            result.error_message = message
            result.executed_at = utcnow()
            db.commit()

    def finish(self, run_id, status, error=None):
        with self.sessions() as db:
            run = db.get(TestRun, run_id)
            run.status = status
            run.error_message = error
            run.completed_at = utcnow()
            db.execute(update(TestResult).where(TestResult.test_run_id == run_id, TestResult.status == 'Pending').values(
                status='Not Executed', executed_at=utcnow(), error_message=error or 'Test did not report a result.'))
            db.commit()
            try:
                generate_reports(db, run, self.settings)
            except Exception:
                logger.exception('Report generation failed for run %s', run_id)
                run.error_message = (run.error_message or '') + ' Report generation failed; check backend logs.'
                db.commit()

    def execute(self, run_id):
        try:
            with self.sessions() as db:
                run = db.get(TestRun, run_id)
                run_ids = [run_id]
                if run.batch_id:
                    run_ids = list(db.scalars(select(TestRun.id).where(TestRun.batch_id == run.batch_id)
                                             .order_by(TestRun.started_at, TestRun.id)))
            # Run browsers one at a time. Workers are shared within each browser.
            for browser_run_id in run_ids:
                if self.stop.is_set():
                    self.finish(browser_run_id, 'Interrupted', 'Backend stopped before this browser run completed.')
                else:
                    self.execute_one(browser_run_id)
        finally:
            self.release()

    def execute_one(self, run_id):
        try:
            with self.sessions() as db:
                run = db.get(TestRun, run_id)
                run.status = 'Running'
                db.commit()
                cases = list(db.scalars(select(TestCase).join(TestResult, TestResult.test_case_id == TestCase.id).where(TestResult.test_run_id == run_id)))
            if run.is_mock:
                for index, case in enumerate(cases):
                    if self.stop.wait(.15):
                        self.finish(run_id, 'Interrupted', 'Backend stopped during execution.')
                        return
                    status = ['Passed', 'Failed', 'Skipped', 'Error', 'Not Executed'][index % 5]
                    self.save_result(run_id, case.id, status, .15, 'Simulated outcome.' if status != 'Passed' else None)
                self.finish(run_id, 'Completed')
            else:
                self.execute_pytest(run, cases)
        except Exception:
            logger.exception('Execution failed for run %s', run_id)
            self.finish(run_id, 'Failed to Start', 'Runner failed. Check backend logs and automation environment.')

    def execute_pytest(self, run, cases):
        with tempfile.TemporaryDirectory(prefix='sentinel-run-') as directory:
            folder = Path(directory)
            selected_file = folder / 'selected.json'
            selected_file.write_text(json.dumps([case.pytest_node_id for case in cases]), encoding='utf-8')
            env = bridge_environment(self.settings, folder)
            env['SENTINEL_SELECTED'] = str(selected_file)
            browser = BROWSERS[run.browser]
            env['SENTINEL_BROWSER_ENGINE'] = browser['engine']
            command = pytest_command(self.settings, run.workers)
            if browser['channel']:
                command.extend(['--browser-channel', browser['channel']])
            if run.browser_mode == 'headed':
                command.append('--headed')
            events_path = folder / 'events.jsonl'
            states = {}
            node_to_id = {case.pytest_node_id: case.id for case in cases}
            processed = 0

            def read_results():
                nonlocal processed
                if not events_path.exists():
                    return
                lines = events_path.read_text(encoding='utf-8').splitlines(keepends=True)
                for line in lines[processed:]:
                    if not line.endswith('\n'):
                        break
                    event = json.loads(line)
                    processed += 1
                    if event['node'] not in node_to_id:
                        continue
                    state = states.setdefault(event['node'], dict(status='Not Executed', duration=0, message=None))
                    state['status'] = phase_result(state['status'], event)
                    state['duration'] += event['duration']
                    if event['message']:
                        state['message'] = event['message']
                    if event['phase'] == 'teardown':
                        self.save_result(run.id, node_to_id[event['node']], state['status'], state['duration'], state['message'])

            # Logs stay in a temporary local file, never in API responses (fixtures may print secrets).
            with (folder / 'pytest.log').open('w', encoding='utf-8') as log:
                process = subprocess.Popen(command, cwd=self.settings.automation_root, env=env, stdout=log, stderr=log)
                started = time.monotonic()
                interrupted = False
                try:
                    while process.poll() is None:
                        read_results()
                        if self.stop.wait(.2) or time.monotonic() - started > self.settings.execution_timeout:
                            interrupted = True
                            break
                finally:
                    if process.poll() is None:
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                        else:
                            process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                read_results()
            if interrupted or process.returncode == 2:
                self.finish(run.id, 'Interrupted', 'Execution was interrupted or exceeded its time limit.')
            elif process.returncode in (0, 1):
                self.finish(run.id, 'Completed')
            else:
                self.finish(run.id, 'Failed to Start',
                            f"Pytest could not complete the {browser_label(run.browser)} run. Check that the selected browser and Playwright dependencies are installed on the execution PC.")

    def recover(self):
        with self.sessions() as db:
            if db.get(RunnerLock, 1) is None:
                db.add(RunnerLock(id=1))
            else:
                db.get(RunnerLock, 1).owner = None
            interrupted = list(db.scalars(select(TestRun.id).where(TestRun.status.in_(ACTIVE))))
            db.commit()
        for run_id in interrupted:
            self.finish(run_id, 'Interrupted', 'Backend restarted before this execution completed.')

    def shutdown(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=15)
