import threading
import time

from sqlalchemy import select

from app.core.security import verify_password
from app.models import TestCase, TestResult, TestRun, User
from app.services.discovery import sync_inventory
from app.services.runner import phase_result
from conftest import login


def wait_run(client, run_id):
    for attempt in range(150):
        response = client.get('/api/runs/' + run_id)
        assert response.status_code == 200, response.text
        if response.json()['status'] not in ('Pending', 'Running'):
            # Report generation commits just after run completion.
            if not response.json()['busy'] and ((response.json()['htmlReport'] and response.json()['pdfReport']) or response.json()['error']):
                return response.json()
        time.sleep(.05)
    raise AssertionError('Execution did not finish.')


def start(client, **changes):
    data = dict(scope_type='all', selection='all', browser_mode='headless', camera_mode='include')
    data.update(changes)
    response = client.post('/api/runs', json=data)
    assert response.status_code == 202, response.text
    return wait_run(client, response.json()['id'])


def test_auth_roles_and_protected_downloads(api):
    client, app = api
    assert client.get('/api/testers').status_code == 401
    assert client.get('/api/runs/missing/reports/pdf').status_code == 401
    assert client.post('/api/auth/login', json=dict(email='admin@northlark.com', password='wrong')).status_code == 401
    login(client, 'admin')
    assert client.post('/api/runs', json={'scope_type': 'all'}).status_code == 403
    created = client.post('/api/testers', json={'name': 'QA Person', 'email': ' QA@NORTHLARK.COM ', 'password': 'qa-password'})
    assert created.status_code == 201
    assert created.json()['role'] == 'tester'
    assert 'password' not in created.text
    assert client.post('/api/testers', json={'name': 'Duplicate', 'email': 'qa@northlark.com', 'password': 'qa-password'}).status_code == 409
    assert client.post('/api/testers', json={'name': 'Injected', 'email': 'bad@example.com', 'password': 'qa-password', 'role': 'admin'}).status_code == 422
    with app.state.sessions() as db:
        tester = db.scalar(select(User).where(User.email == 'qa@northlark.com'))
        assert verify_password('qa-password', tester.password_hash)
        assert tester.password_hash != 'qa-password'
    assert client.post('/api/auth/logout').status_code == 204
    assert client.get('/api/auth/me').status_code == 401
    assert client.post('/api/auth/login', json={'email': 'qa@northlark.com', 'password': 'qa-password'}).status_code == 200
    assert client.get('/api/testers').status_code == 403
    assert client.post('/api/testers', json={'name': 'No Access', 'email': 'no@example.com', 'password': 'qa-password'}).status_code == 403
    assert client.post('/api/auth/logout', headers={'Origin': 'https://untrusted.example'}).status_code == 403


def test_discovery_keeps_identity_and_history(api):
    client, app = api
    login(client)
    assert client.post('/api/discovery').json()['count'] == 15
    first = client.get('/api/tests').json()['items']
    assert all(case['executionCount'] == 0 for case in first)
    assert all(case['latestStatus'] == 'Not Run' for case in first)
    client.post('/api/discovery')
    assert [(case['id'], case['code']) for case in first] == [(case['id'], case['code']) for case in client.get('/api/tests').json()['items']]
    run = start(client, scope_type='module', scope_value='Login')
    assert run['status'] == 'Completed'
    with app.state.sessions() as db:
        cases = list(db.scalars(select(TestCase).where(TestCase.is_mock.is_(True))))
        record = dict(pytest_node_id='mock::new', name='New test', module='Login', category='Positive', requires_real_camera=False, camera_classified=True)
        sync_inventory(db, [record], [], True)
        assert db.get(TestCase, first[0]['id']).is_active is False
        assert len(list(db.scalars(select(TestResult)))) == 2
    visible = client.get('/api/tests').json()['items']
    assert visible[0]['executionCount'] == 0
    assert visible[0]['latestStatus'] == 'Not Run'


def test_all_outcomes_counts_latest_three_and_reports(api):
    client, app = api
    login(client)
    run = start(client)
    assert run['status'] == 'Completed'  # Failed assertions are not a runner failure.
    assert set(item['status'] for item in run['results']) == {'Passed', 'Failed', 'Skipped', 'Error', 'Not Executed'}
    assert len(run['results']) == 15
    assert all(case['executionCount'] == 1 for case in client.get('/api/tests').json()['items'])
    for attempt in range(3):
        start(client, scope_type='module', scope_value='Login', camera_mode='exclude')
    login_cases = client.get('/api/tests', params={'module': 'Login'}).json()['items']
    assert all(case['executionCount'] == 4 and len(case['recentResults']) == 3 for case in login_cases)
    assert len(client.get('/api/tests/' + str(login_cases[0]['id'])).json()['recentResults']) == 4
    others = client.get('/api/tests', params={'module': 'Home'}).json()['items']
    assert all(case['executionCount'] == 1 for case in others)
    html = client.get(f"/api/runs/{run['id']}/reports/html")
    assert html.status_code == 200 and 'SIMULATED' in html.text
    pdf = client.get(f"/api/runs/{run['id']}/reports/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
    client.post('/api/auth/logout')
    assert client.get(f"/api/runs/{run['id']}/reports/pdf").status_code == 401


def test_busy_rejection_and_release(api):
    client, app = api
    login(client)
    gate = threading.Event()
    original = app.state.runner.execute
    def delayed(run_id):
        gate.wait(timeout=5)
        original(run_id)
    app.state.runner.execute = delayed
    first = client.post('/api/runs', json={'scope_type': 'module', 'scope_value': 'Login'})
    assert first.status_code == 202
    try:
        assert client.post('/api/runs', json={'scope_type': 'module', 'scope_value': 'Home'}).status_code == 409
        assert client.post('/api/discovery').status_code == 409
    finally:
        gate.set()
    wait_run(client, first.json()['id'])
    assert client.post('/api/discovery').status_code == 200


def test_camera_and_category_selection(api):
    client, app = api
    login(client)
    run = start(client, scope_type='module', scope_value='Onboarding', camera_mode='only', selection='positive')
    assert run['total'] == 1
    assert 'camera' in run['results'][0]['name']
    assert client.post('/api/runs', json={'scope_type': 'module', 'scope_value': 'Login', 'camera_mode': 'only'}).status_code == 422
    assert client.post('/api/runs', json={'scope_type': 'all', 'browser_mode': 'unsafe'}).status_code == 422


def test_restart_finalizes_selected_tests_and_releases_busy_state(api):
    client, app = api
    user = login(client)
    client.post('/api/discovery')
    with app.state.sessions() as db:
        case = db.scalar(select(TestCase))
        run = TestRun(executed_by_user_id=user['id'], scope_type='test', scope_value=case.case_code,
                      selection='all', browser_mode='headless', camera_mode='exclude', status='Running', is_mock=True)
        db.add(run)
        db.flush()
        db.add(TestResult(test_run_id=run.id, test_case_id=case.id))
        run_id = run.id
        db.commit()
    app.state.runner.recover()
    data = client.get('/api/runs/' + run_id).json()
    assert data['status'] == 'Interrupted'
    assert data['results'][0]['status'] == 'Not Executed'
    assert client.get('/api/tests/' + str(case.id)).json()['executionCount'] == 1
    assert client.post('/api/discovery').status_code == 200


def test_teardown_error_overrides_pass_and_setup_errors_are_errors():
    assert phase_result('Passed', {'phase': 'teardown', 'outcome': 'failed'}) == 'Error'
    assert phase_result('Not Executed', {'phase': 'setup', 'outcome': 'failed'}) == 'Error'
    assert phase_result('Not Executed', {'phase': 'setup', 'outcome': 'skipped'}) == 'Skipped'


def test_runner_exception_records_not_executed_and_releases_lock(api):
    client, app = api
    login(client)
    original = app.state.runner.save_result
    def failed_result(*args, **kwargs):
        raise RuntimeError('Intentional runner failure')
    app.state.runner.save_result = failed_result
    run = start(client, scope_type='module', scope_value='Login')
    assert run['status'] == 'Failed to Start'
    assert all(result['status'] == 'Not Executed' for result in run['results'])
    assert all(case['executionCount'] == 1 for case in client.get('/api/tests', params={'module': 'Login'}).json()['items'])
    app.state.runner.save_result = original
    assert client.post('/api/discovery').status_code == 200
