import subprocess

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text

from app.core.config import Settings
from app.db.migrations import upgrade_schema
from app.models import TestCase, TestResult, TestRun
from app.schemas import RunInput
from conftest import login
from test_backend import start


def test_worker_validation_and_saved_mock_setting(api):
    client, app = api
    login(client)
    for value in (0, -1, 33, 1.5, '2', True, None):
        response = client.post('/api/runs', json={'scope_type': 'all', 'workers': value})
        assert response.status_code == 422
    run = start(client, workers=4)
    assert run['workers'] == 4
    with app.state.sessions() as db:
        assert db.get(TestRun, run['id']).workers == 4
    assert 'Workers: 4' in client.get(f"/api/runs/{run['id']}/reports/html").text


def test_worker_column_upgrade_preserves_existing_runs(tmp_path):
    engine = create_engine('sqlite:///' + (tmp_path / 'old.db').as_posix())
    with engine.begin() as db:
        db.execute(text('CREATE TABLE test_runs (id VARCHAR(36) PRIMARY KEY)'))
        db.execute(text("INSERT INTO test_runs (id) VALUES ('existing-run')"))
    upgrade_schema(engine)
    upgrade_schema(engine)
    with engine.connect() as db:
        assert db.execute(text('SELECT id, workers FROM test_runs')).one() == ('existing-run', 1)
    engine.dispose()


def test_missing_xdist_rejects_parallel_run_and_releases_lock(api, monkeypatch):
    client, app = api
    runner = app.state.runner
    runner.settings.executor = 'pytest'
    monkeypatch.setattr('app.services.discovery.subprocess.run',
                        lambda *args, **kwargs: subprocess.CompletedProcess([], 1))
    with pytest.raises(HTTPException, match='pytest-xdist'):
        runner.start(None, RunInput(scope_type='all', workers=2))
    assert not runner.lock.locked()
    runner.settings.executor = 'mock'


def test_worker_preview_respects_scope_and_filters_without_creating_runs(api):
    client, app = api
    assert client.post('/api/runs/preview', json={'scope_type': 'all'}).status_code == 401
    login(client)
    assert client.post('/api/runs/preview', json={'scope_type': 'all'}).status_code == 422
    assert client.post('/api/discovery').status_code == 200
    for options, count in [
        ({'scope_type': 'all'}, 14),
        ({'scope_type': 'all', 'selection': 'positive'}, 7),
        ({'scope_type': 'module', 'scope_value': 'Login'}, 2),
        ({'scope_type': 'module', 'scope_value': 'Onboarding', 'camera_mode': 'only'}, 1),
        ({'scope_type': 'all', 'camera_mode': 'include'}, 15),
    ]:
        response = client.post('/api/runs/preview', json=options)
        assert response.status_code == 200, response.text
        assert response.json()['selectedCount'] == count
        assert response.json()['recommendedWorkers'] == 1
    case = client.get('/api/tests', params={'module': 'Login'}).json()['items'][0]
    response = client.post('/api/runs/preview', json={'scope_type': 'test', 'scope_value': case['code']})
    assert response.json()['selectedCount'] == 1
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(TestRun)) == 0
        assert db.scalar(select(func.count()).select_from(TestResult)) == 0


def test_worker_estimate_caps_cpu_and_recommends_one_for_shared_camera(monkeypatch):
    from app.services.selection import worker_recommendation

    cases = [TestCase(requires_real_camera=False, camera_classified=True) for _ in range(100)]
    monkeypatch.setattr('app.services.selection.os.cpu_count', lambda: 4)
    assert worker_recommendation(cases)['recommendedWorkers'] == 4
    cases[0].requires_real_camera = True
    assert worker_recommendation(cases)['recommendedWorkers'] == 1
    cases[0].requires_real_camera = False
    cases[0].camera_classified = False
    assert worker_recommendation(cases)['recommendedWorkers'] == 1
