from datetime import timedelta
from pathlib import Path
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.core.security import ADMIN_EMAIL, admin_only, current_user, hash_password, tester_only, token_hash, user_profile, verify_password
from app.db.database import get_db, utcnow
from app.models import DiscoveryInfo, LoginSession, RunnerLock, TestCase, TestRun, User
from app.schemas import LoginInput, RunInput, TesterInput
from app.services.history import case_profile, dashboard_profile, latest_result_status, run_profile
from app.services.selection import selected_cases, worker_recommendation
from app.services.account_security import audit

router = APIRouter(prefix='/api')


@router.post('/auth/login')
def login(data: LoginInput, request: Request, response: Response, db=Depends(get_db)):
    address = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    attempts = request.app.state.login_attempts
    with request.app.state.login_lock:
        # Expire inactive entries to keep the in-process limiter bounded.
        for key in list(attempts):
            attempts[key] = [timestamp for timestamp in attempts[key] if now - timestamp < 60]
            if not attempts[key]:
                del attempts[key]
        if len(attempts.get(address, [])) >= 20:
            raise HTTPException(429, 'Too many login attempts. Try again in a minute.')
        attempts.setdefault(address, []).append(now)
    user = db.scalar(select(User).where(User.email == data.email).with_for_update())
    valid = verify_password(data.password, user.password_hash if user else request.app.state.dummy_password)
    if not user or not valid or not user.is_active or (user.role == 'admin' and user.email != ADMIN_EMAIL):
        audit(db, 'login_failed', target=user)
        db.commit()
        raise HTTPException(401, 'Incorrect email or password.')
    previous = request.cookies.get('sentinel_session')
    if previous:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(previous)))
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= utcnow()))
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=utcnow() + timedelta(hours=8)))
    audit(db, 'login_succeeded', user)
    db.commit()
    response.set_cookie('sentinel_session', token, httponly=True, secure=request.app.state.settings.secure_cookies,
                        samesite='strict', max_age=8 * 3600, path='/')
    return user_profile(user)


@router.post('/auth/logout', status_code=204)
def logout(request: Request, response: Response, db=Depends(get_db)):
    token = request.cookies.get('sentinel_session')
    if token:
        session = db.get(LoginSession, token_hash(token))
        if session:
            audit(db, 'logout', db.get(User, session.user_id))
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(token)))
        db.commit()
    response.delete_cookie('sentinel_session', path='/')


@router.get('/auth/me')
def me(user=Depends(current_user)):
    return user_profile(user)


@router.get('/testers')
def testers(user=Depends(admin_only), db=Depends(get_db)):
    return [user_profile(tester) for tester in db.scalars(select(User).where(User.role == 'tester').order_by(User.created_at.desc()))]


@router.get('/dashboard')
def dashboard(request: Request, user=Depends(current_user), db=Depends(get_db)):
    data = dashboard_profile(db, request.app.state.settings)
    info = db.get(DiscoveryInfo, 1)
    active = db.scalar(select(TestRun).where(TestRun.status.in_(('Pending', 'Running'))))
    data.update(provider=request.app.state.settings.executor, warnings=info.warnings if info else [],
                discoveredAt=info.discovered_at if info else None, activeRun=run_profile(db, active) if active else None,
                busy=bool(db.get(RunnerLock, 1).owner) or request.app.state.runner.lock.locked())
    return data


@router.post('/discovery')
def discover(request: Request, user=Depends(current_user)):
    return request.app.state.runner.synchronize()


@router.get('/tests')
def tests(request: Request, module: str | None = None, category: str | None = None, status: str | None = None,
          search: str = '', page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
          user=Depends(current_user), db=Depends(get_db)):
    query = select(TestCase).where(TestCase.is_active.is_(True), TestCase.is_mock == (request.app.state.settings.executor == 'mock'))
    if module:
        query = query.where(TestCase.module == module)
    if category:
        query = query.where(TestCase.category == category)
    if search.strip():
        pattern = '%' + search.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        query = query.where(TestCase.name.ilike(pattern, escape='\\') | TestCase.case_code.ilike(pattern, escape='\\'))
    if status:
        query = query.where(func.coalesce(latest_result_status(), 'Not Run') == status)
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    cases = list(db.scalars(query.order_by(TestCase.id).offset((page - 1) * page_size).limit(page_size)))
    return dict(items=[case_profile(db, case) for case in cases], total=count, page=page, pageSize=page_size)


@router.get('/tests/{case_id}')
def test_detail(case_id: int, user=Depends(current_user), db=Depends(get_db)):
    case = db.get(TestCase, case_id)
    if not case:
        raise HTTPException(404, 'Test case not found.')
    return case_profile(db, case, limit=4)


@router.post('/runs/preview')
def preview_run(data: RunInput, request: Request, user=Depends(tester_only), db=Depends(get_db)):
    try:
        cases = selected_cases(db, request.app.state.settings, data)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return worker_recommendation(cases)


@router.post('/runs', status_code=202)
def start_run(data: RunInput, request: Request, user=Depends(tester_only)):
    run_id = request.app.state.runner.start(user, data)
    return dict(id=run_id)


@router.get('/runs')
def runs(request: Request, page: int = Query(1, ge=1), user=Depends(current_user), db=Depends(get_db)):
    query = select(TestRun).where(TestRun.is_mock == (request.app.state.settings.executor == 'mock'))
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(TestRun.started_at.desc()).offset((page - 1) * 30).limit(30))
    return dict(items=[run_profile(db, run) for run in items], total=count, page=page)


@router.get('/runs/{run_id}')
def run_detail(run_id: str, request: Request, user=Depends(current_user), db=Depends(get_db)):
    run = db.get(TestRun, run_id)
    if not run:
        raise HTTPException(404, 'Execution not found.')
    data = run_profile(db, run, details=True)
    data['browserRuns'] = []
    if run.batch_id:
        browser_runs = db.scalars(select(TestRun).where(TestRun.batch_id == run.batch_id)
                                 .order_by(TestRun.started_at, TestRun.id))
        data['browserRuns'] = [dict(id=item.id, browser=item.browser, status=item.status) for item in browser_runs]
    data['busy'] = bool(db.get(RunnerLock, 1).owner) or request.app.state.runner.lock.locked()
    return data


@router.get('/runs/{run_id}/reports/{kind}')
def report(run_id: str, kind: str, request: Request, download: bool = True,
           user=Depends(current_user), db=Depends(get_db)):
    if kind not in ('html', 'pdf'):
        raise HTTPException(404, 'Report format not found.')
    run = db.get(TestRun, run_id)
    stored = getattr(run, kind + '_report_path', None) if run else None
    if not stored:
        raise HTTPException(404, 'Report is not available yet.')
    path = Path(stored).resolve()
    root = request.app.state.settings.reports_root.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404, 'Report not found.')
    return FileResponse(path, media_type='text/html' if kind == 'html' else 'application/pdf',
                        filename=f'{run.id}.{kind}', content_disposition_type='attachment' if download else 'inline',
                        headers={'Content-Security-Policy': "sandbox; default-src 'none'; style-src 'unsafe-inline'", 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})
