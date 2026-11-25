import json
from pathlib import Path
import threading
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import Settings
from app.main import create_app
from app.models import TestRun
from app.db.migrations import upgrade_schema
from app.services.discovery import collect_tests
from app.setup import provision
from conftest import login, TEST_PASSWORD
from test_backend import start, wait_run


def test_browser_migration_preserves_existing_runs(tmp_path):
    engine = create_engine('sqlite:///' + (tmp_path / 'legacy.db').as_posix())
    with engine.begin() as db:
        db.execute(text('CREATE TABLE test_runs (id VARCHAR(36) PRIMARY KEY, workers INTEGER NOT NULL)'))
        db.execute(text("INSERT INTO test_runs VALUES ('old-run', 3)"))
    upgrade_schema(engine)
    upgrade_schema(engine)
    with engine.connect() as db:
        assert db.execute(text('SELECT id, workers, browser, batch_id FROM test_runs')).one() == ('old-run', 3, 'chromium', None)
    engine.dispose()


def test_browser_validation_and_default(api):
    client, _ = api
    login(client)
    for browsers in ([], ['safari'], ['chrome', 'chrome'], 'chrome', [None]):
        assert client.post('/api/runs', json={'scope_type': 'all', 'browsers': browsers}).status_code == 422
    run = start(client, scope_type='module', scope_value='Login')
    assert run['browser'] == 'chromium'
    assert run['browserLabel'] == 'Chromium'


def test_multiple_browsers_keep_lock_history_and_separate_reports(api, monkeypatch):
    client, app = api
    login(client)
    gate = threading.Event()
    second_started = threading.Event()
    original = app.state.runner.execute_one
    calls = []

    def execute_one(run_id):
        calls.append(run_id)
        if len(calls) == 2:
            second_started.set()
            gate.wait(timeout=10)
        original(run_id)

    monkeypatch.setattr(app.state.runner, 'execute_one', execute_one)
    response = client.post('/api/runs', json={'scope_type': 'module', 'scope_value': 'Login',
                                            'browsers': ['chrome', 'edge', 'webkit'], 'workers': 2})
    assert response.status_code == 202, response.text
    first_id = response.json()['id']
    try:
        assert second_started.wait(timeout=10)
        first = client.get('/api/runs/' + first_id).json()
        assert first['status'] == 'Completed'
        assert first['busy']
        assert [run['browser'] for run in first['browserRuns']] == ['chrome', 'edge', 'webkit']
        assert first['browserRuns'][1]['status'] == 'Pending'
        assert client.post('/api/runs', json={'scope_type': 'all'}).status_code == 409
        assert client.post('/api/discovery').status_code == 409
    finally:
        gate.set()
    wait_run(client, first_id)

    runs = [client.get('/api/runs/' + item['id']).json() for item in first['browserRuns']]
    assert len({run['batchId'] for run in runs}) == 1
    assert all(run['status'] == 'Completed' and run['workers'] == 2 for run in runs)
    for run in runs:
        html = client.get(f"/api/runs/{run['id']}/reports/html")
        assert f"Browser: {run['browserLabel']}" in html.text
        assert client.get(f"/api/runs/{run['id']}/reports/pdf").content.startswith(b'%PDF')
    cases = client.get('/api/tests', params={'module': 'Login'}).json()['items']
    assert len(cases) == 2
    assert all(case['executionCount'] == 3 for case in cases)
    assert [result['browser'] for result in cases[0]['recentResults']] == ['webkit', 'edge', 'chrome']
    assert client.post('/api/discovery').status_code == 200


def test_failed_browser_does_not_cancel_remaining_browsers(api, monkeypatch):
    client, app = api
    login(client)
    original = app.state.runner.save_result

    def save_result(run_id, *args, **kwargs):
        with app.state.sessions() as db:
            if db.get(TestRun, run_id).browser == 'chrome':
                raise RuntimeError('Simulated browser failure')
        original(run_id, *args, **kwargs)

    monkeypatch.setattr(app.state.runner, 'save_result', save_result)
    first = start(client, scope_type='module', scope_value='Login', browsers=['chrome', 'edge'])
    runs = [client.get('/api/runs/' + item['id']).json() for item in first['browserRuns']]
    assert [run['status'] for run in runs] == ['Failed to Start', 'Completed']
    assert all(result['status'] == 'Not Executed' for result in runs[0]['results'])
    assert all(case['executionCount'] == 2 for case in client.get('/api/tests', params={'module': 'Login'}).json()['items'])


def test_real_playwright_fixtures_use_selected_engine_and_channel(tmp_path):
    # Only a disposable suite is collected/executed; no real QA site is visited.
    python = Path(__file__).resolve().parents[3] / 'testing' / '.venv' / 'Scripts' / 'python.exe'
    if not python.is_file():
        pytest.skip('The automation environment is not available.')
    root = tmp_path / 'automation'
    (root / 'tests').mkdir(parents=True)
    (root / 'tests' / 'test_login.py').write_text('''import os
import pytest

def test_browser(browser_name, browser_type, browser_channel, browser_type_launch_args):
    assert browser_name == os.environ['SENTINEL_BROWSER_ENGINE']
    assert browser_type.name == browser_name
    assert browser_type_launch_args['headless'] is False
    assert browser_channel in ('chrome', 'msedge', None)
    if browser_name == 'webkit':
        assert browser_channel is None

@pytest.mark.skip_browser('webkit')
def test_browser_marker(page):
    # Override page below: inspect marker behaviour without launching browsers.
    assert page == 'disposable'

@pytest.fixture
def page(browser_name):
    return 'disposable'
''', encoding='utf-8')
    metadata = tmp_path / 'metadata.json'
    metadata.write_text('{}', encoding='utf-8')
    settings = Settings(database_url='sqlite:///' + (tmp_path / 'test.db').as_posix(), testing=True,
                        executor='pytest', automation_root=root, automation_python=str(python),
                        metadata_file=metadata, reports_root=tmp_path / 'reports')
    records, _ = collect_tests(settings)
    assert len(records) == 2
    assert all('[chromium]' in record['pytest_node_id'] for record in records)
    metadata.write_text(json.dumps({record['pytest_node_id']: {'requires_real_camera': False} for record in records}), encoding='utf-8')
    with TestClient(create_app(settings)) as client:
        app = client.app
        with app.state.sessions() as db:
            provision(db, 'Tester', 'tester@northlark.com', TEST_PASSWORD, 'tester')
        login(client)
        response = client.post('/api/runs', json={'scope_type': 'all', 'browsers': ['chrome', 'edge', 'webkit'],
                                                 'browser_mode': 'headed', 'workers': 2})
        assert response.status_code == 202, response.text
        # Three independent pytest/xdist startups take longer than one run.
        for attempt in range(600):
            first = client.get('/api/runs/' + response.json()['id']).json()
            if not first['busy']:
                break
            time.sleep(.1)
        assert not first['busy'], 'Browser batch did not finish.'
        runs = [client.get('/api/runs/' + item['id']).json() for item in first['browserRuns']]
        assert [run['status'] for run in runs] == ['Completed'] * 3
        assert [run['summary']['Passed'] for run in runs] == [2, 2, 1]
        assert runs[2]['summary']['Skipped'] == 1
        cases = client.get('/api/tests').json()['items']
        assert len(cases) == 2
        assert all(case['executionCount'] == 3 for case in cases)
