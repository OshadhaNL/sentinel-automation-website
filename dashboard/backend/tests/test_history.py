import pytest
from sqlalchemy import select

from app.models import TestCase, TestResult, TestRun, User
from app.services.history import case_profile, dashboard_profile, run_profile


@pytest.mark.parametrize('statuses,expected', [
    ([], 'Not Executed'),
    (['Passed', 'Skipped'], 'Passed'),
    (['Skipped', 'Not Executed'], 'Skipped'),
    (['Passed', 'Error'], 'Failed'),
    (['Passed', 'Failed', 'Pending'], 'Failed'),
    (['Passed', 'Pending'], 'Running'),
    (['Not Executed'], 'Not Executed'),
])
def test_run_summary_matches_details(api, statuses, expected):
    _, app = api
    with app.state.sessions() as db:
        tester = db.scalar(select(User).where(User.role == 'tester'))
        run = TestRun(executed_by_user_id=tester.id, scope_type='all', selection='all',
                      browser_mode='headless', camera_mode='exclude', status='Running', is_mock=True)
        db.add(run)
        db.flush()
        for index, status in enumerate(statuses):
            case = TestCase(case_code=f'TC-{index}', name=f'Test {index}', module='Login',
                            category='Positive', pytest_node_id=f'mock::{index}', is_mock=True)
            db.add(case)
            db.flush()
            db.add(TestResult(test_run_id=run.id, test_case_id=case.id, status=status))
        db.commit()

        summary = run_profile(db, run)
        details = run_profile(db, run, details=True)
        assert details.pop('results') is not None
        assert summary == details
        assert summary['result'] == expected
        assert summary['total'] == len(statuses)
        assert summary['completed'] == len(statuses) - statuses.count('Pending')
        assert summary['summary'] == {status: statuses.count(status) for status in
                                     ['Passed', 'Failed', 'Skipped', 'Error', 'Not Executed', 'Pending']}
        assert summary['modules'] == (['Login'] if statuses else [])


def test_history_counts_and_latest_order_are_preserved(api):
    _, app = api
    statuses = ['Passed', 'Failed', 'Skipped', 'Error', 'Not Executed', 'Pending']
    with app.state.sessions() as db:
        tester = db.scalar(select(User).where(User.role == 'tester'))
        case = TestCase(case_code='TC-HISTORY', name='History test', module='Onboarding',
                        category='Positive', pytest_node_id='mock::history', is_mock=True)
        db.add(case)
        db.flush()
        for status in statuses:
            run = TestRun(executed_by_user_id=tester.id, scope_type='test', scope_value=case.case_code,
                          selection='all', browser_mode='headless', camera_mode='exclude', is_mock=True)
            db.add(run)
            db.flush()
            db.add(TestResult(test_run_id=run.id, test_case_id=case.id, status=status))
        db.commit()

        profile = case_profile(db, case)
        assert profile['executionCount'] == 5
        assert profile['latestStatus'] == 'Not Executed'
        assert [result['status'] for result in profile['recentResults']] == ['Not Executed', 'Error', 'Skipped']
        assert len(case_profile(db, case, limit=4)['recentResults']) == 4
        dashboard = dashboard_profile(db, app.state.settings)
        assert dashboard['totals']['total'] == 1
        assert dashboard['totals']['notExecuted'] == 1
        assert next(module for module in dashboard['modules'] if module['name'] == 'Onboarding')['total'] == 1
