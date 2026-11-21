from sqlalchemy import func, select

from app.db.database import utc
from app.models import TestCase, TestResult, TestRun, User


def result_profile(db, result):
    run = db.get(TestRun, result.test_run_id)
    tester = db.get(User, run.executed_by_user_id)
    return dict(status=result.status, duration=result.duration_seconds, error=result.error_message,
                executedAt=utc(result.executed_at).isoformat(), runId=run.id,
                tester=tester.name, mode=run.browser_mode.title(), workers=run.workers, isMock=run.is_mock,
                htmlReport=bool(run.html_report_path), pdfReport=bool(run.pdf_report_path))


def case_profile(db, case, limit=3):
    query = select(TestResult).where(TestResult.test_case_id == case.id, TestResult.status != 'Pending')
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    recent = list(db.scalars(query.order_by(TestResult.id.desc()).limit(limit)))
    return dict(id=case.id, code=case.case_code, name=case.name, module=case.module, category=case.category,
                pytestNodeId=case.pytest_node_id, requiresRealCamera=case.requires_real_camera,
                cameraClassified=case.camera_classified, isActive=case.is_active, isMock=case.is_mock,
                executionCount=count, latestStatus=recent[0].status if recent else 'Not Run',
                recentResults=[result_profile(db, result) for result in recent])


def run_profile(db, run, details=False):
    results = list(db.scalars(select(TestResult).where(TestResult.test_run_id == run.id).order_by(TestResult.id)))
    outcomes = [result.status for result in results]
    summary = {status: outcomes.count(status) for status in ['Passed', 'Failed', 'Skipped', 'Error', 'Not Executed', 'Pending']}
    outcome = 'Not Executed'
    if summary['Failed'] or summary['Error']:
        outcome = 'Failed'
    elif summary['Pending']:
        outcome = run.status
    elif summary['Passed']:
        outcome = 'Passed'
    elif summary['Skipped']:
        outcome = 'Skipped'
    tester = db.get(User, run.executed_by_user_id)
    cases = {case.id: case for case in db.scalars(select(TestCase).where(TestCase.id.in_([result.test_case_id for result in results])))}
    selected_modules = sorted({case.module for case in cases.values()})
    profile = dict(id=run.id, label='RUN-' + run.id[:8].upper(), modules=selected_modules, module=run.scope_value if run.scope_type == 'module' else 'All Systems' if run.scope_type == 'all' else 'Individual Test',
                   scope={'all': 'All Tests', 'positive': 'Happy Path', 'negative': 'Negative Tests'}[run.selection],
                   executedAt=utc(run.started_at).isoformat(), completedAt=utc(run.completed_at).isoformat() if run.completed_at else None,
                   tester=tester.name, mode=run.browser_mode.title(), cameraMode=run.camera_mode, workers=run.workers,
                   status=run.status, result=outcome, isMock=run.is_mock, summary=summary,
                   total=len(results), completed=len(results) - summary['Pending'], error=run.error_message,
                   duration=round((utc(run.completed_at) - utc(run.started_at)).total_seconds(), 2) if run.completed_at else 0,
                   htmlReport=bool(run.html_report_path), pdfReport=bool(run.pdf_report_path))
    if details:
        profile['results'] = [dict(testCaseId=result.test_case_id, code=cases[result.test_case_id].case_code,
                                   name=cases[result.test_case_id].name, **result_profile(db, result)) for result in results]
    return profile


def dashboard_profile(db, settings):
    latest = select(TestResult.status).where(TestResult.test_case_id == TestCase.id, TestResult.status != 'Pending').order_by(TestResult.id.desc()).limit(1).scalar_subquery()
    cases = db.execute(select(TestCase.module, latest).where(TestCase.is_active.is_(True), TestCase.is_mock == (settings.executor == 'mock'))).all()
    names = ['Login', 'Home', 'Dashboard', 'Onboarding', 'Profiles', 'Transactions', 'Screening']
    names += sorted({name for name, status in cases} - set(names))
    modules = []
    for index, name in enumerate(names):
        statuses = [status or 'Not Run' for module, status in cases if module == name]
        modules.append(dict(name=name, total=len(statuses), passed=statuses.count('Passed'), failed=statuses.count('Failed'),
                            skipped=statuses.count('Skipped'), error=statuses.count('Error'),
                            notExecuted=statuses.count('Not Executed') + statuses.count('Not Run'),
                            color=f'var(--chart-{index % 7 + 1})', icon=name.lower() if name in names[:7] else 'layers'))
    totals = {key: sum(module[key] for module in modules) for key in ('total', 'passed', 'failed', 'skipped', 'error', 'notExecuted')}
    runs = list(db.scalars(select(TestRun).where(TestRun.is_mock == (settings.executor == 'mock')).order_by(TestRun.started_at.desc()).limit(30)))
    return dict(modules=modules, totals=totals, runs=[run_profile(db, run) for run in runs])
