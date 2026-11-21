import json
import sys
import time

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.models import TestCase
from app.services.discovery import collect_tests
from app.setup import provision
from conftest import login
from test_backend import start


@pytest.mark.parametrize('workers', [1, 2])
def test_actual_pytest_bridge_without_touching_sentinel(tmp_path, workers):
    """Run a tiny disposable suite, not the user's real QA application."""
    root = tmp_path / 'automation'
    (root / 'tests').mkdir(parents=True)
    (root / 'conftest.py').write_text('''import os
from pathlib import Path

def pytest_runtest_call(item):
    worker = os.getenv('PYTEST_XDIST_WORKER', 'main')
    count = os.getenv('PYTEST_XDIST_WORKER_COUNT', '1')
    (Path(__file__).parent / ('worker-' + worker + '.txt')).write_text(count)
''', encoding='utf-8')
    (root / 'tests' / 'test_login.py').write_text('''import pytest

def test_pass():
    assert True

def test_fail():
    assert False, "intentional fixture failure"

@pytest.mark.skip(reason="intentional skip")
def test_skip():
    pass

@pytest.fixture
def broken_setup():
    raise RuntimeError("intentional setup error")

def test_error(broken_setup):
    pass

@pytest.fixture
def bad_teardown():
    yield
    raise RuntimeError("intentional teardown error")

def test_teardown(bad_teardown):
    assert True

@pytest.mark.parametrize("value", [1, 2])
def test_parameters(value):
    assert value > 0
''', encoding='utf-8')
    metadata = tmp_path / 'metadata.json'
    metadata.write_text('{}', encoding='utf-8')
    settings = Settings(database_url='sqlite:///' + (tmp_path / 'database.db').as_posix(), testing=True,
                        executor='pytest', automation_root=root, automation_python=sys.executable,
                        metadata_file=metadata, reports_root=tmp_path / 'reports')
    records, warnings = collect_tests(settings)
    assert len(records) == 7
    assert len({record['pytest_node_id'] for record in records}) == 7
    assert any('[1]' in record['pytest_node_id'] for record in records)
    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.sessions() as db:
            provision(db, 'Tester', 'tester@northlark.com', 'password123', 'tester')
        login(client)
        run = start(client, camera_mode='exclude', workers=workers)
        assert run['workers'] == workers
        worker_files = list(root.glob('worker-*.txt'))
        assert len(worker_files) == workers
        assert all(path.read_text() == str(workers) for path in worker_files)
        assert not run['isMock']
        assert run['status'] == 'Completed'
        assert run['summary']['Passed'] == 3
        assert run['summary']['Failed'] == 1
        assert run['summary']['Skipped'] == 1
        assert run['summary']['Error'] == 2
        assert run['htmlReport'] and run['pdfReport']
        ids = [(case['id'], case['code']) for case in client.get('/api/tests').json()['items']]
        # A collection failure must not remove or deactivate the previous inventory.
        (root / 'tests' / 'test_invalid.py').write_text('invalid syntax !!!', encoding='utf-8')
        assert client.post('/api/discovery').status_code == 422
        assert ids == [(case['id'], case['code']) for case in client.get('/api/tests').json()['items']]
    # Persistent sessions, accounts and results survive a new API instance.
    restarted = create_app(settings)
    with TestClient(restarted) as client:
        login(client)
        results = client.get('/api/tests').json()['items']
        assert len(results) == 7
        assert all(case['executionCount'] == 1 for case in results)
        assert all(case['recentResults'][0]['workers'] == workers for case in results)


def test_unknown_categories_and_camera_dependencies_are_not_silently_guessed(tmp_path):
    root = tmp_path / 'automation'
    (root / 'tests').mkdir(parents=True)
    (root / 'tests' / 'test_individual_onboarding.py').write_text('def test_documents():\n    assert True\n', encoding='utf-8')
    metadata = tmp_path / 'metadata.json'
    metadata.write_text('{}', encoding='utf-8')
    settings = Settings(database_url='sqlite:///' + (tmp_path / 'database.db').as_posix(), testing=True,
                        executor='pytest', automation_root=root, automation_python=sys.executable,
                        metadata_file=metadata, reports_root=tmp_path / 'reports')
    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.sessions() as db:
            provision(db, 'Tester', 'tester@northlark.com', 'password123', 'tester')
        login(client)
        assert client.post('/api/runs', json={'scope_type': 'all', 'selection': 'positive'}).status_code == 422
        assert client.post('/api/runs', json={'scope_type': 'all', 'camera_mode': 'exclude'}).status_code == 422
        node = 'tests/test_individual_onboarding.py::test_documents'
        metadata.write_text(json.dumps({node: {'category': 'Positive', 'requires_real_camera': False}}), encoding='utf-8')
        run = start(client, selection='positive', camera_mode='exclude')
        assert run['total'] == 1 and run['results'][0]['status'] == 'Passed'
