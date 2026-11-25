from contextlib import asynccontextmanager
import threading

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.api import router
from app.api.routes.accounts import router as accounts_router
from app.core.config import Settings
from app.core.security import hash_password
from app.db.database import Base, make_database
from app.db.migrations import upgrade_schema
from app.services.runner import Runner


def create_app(settings=None):
    settings = settings or Settings()
    engine, sessions = make_database(settings)

    @asynccontextmanager
    async def lifespan(app):
        process_lock = None
        try:
            if engine.dialect.name == 'postgresql':
                # Refuse a second backend worker before recovering unfinished runs.
                process_lock = engine.connect()
                if not process_lock.scalar(text('SELECT pg_try_advisory_lock(739104221)')):
                    raise RuntimeError('Another Sentinel backend is running. Use exactly one backend process.')
                process_lock.commit()
            Base.metadata.create_all(engine)
            upgrade_schema(engine)
            app.state.runner.recover()
            yield
        finally:
            app.state.runner.shutdown()
            if process_lock is not None:
                process_lock.close()
            engine.dispose()

    app = FastAPI(title='Sentinel Dashboard API', lifespan=lifespan)
    app.state.settings = settings
    app.state.sessions = sessions
    app.state.engine = engine
    app.state.runner = Runner(sessions, settings)
    app.state.dummy_password = hash_password('invalid-account-placeholder')
    app.state.login_attempts = {}
    app.state.login_lock = threading.Lock()
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=True,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.middleware('http')
    async def trusted_origin(request: Request, call_next):
        origin = request.headers.get('origin')
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and origin and origin not in settings.allowed_origins:
            return JSONResponse({'detail': 'Untrusted request origin.'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        return JSONResponse({'detail': 'Database unavailable. Check PostgreSQL and DATABASE_URL.'}, status_code=503)

    @app.get('/health')
    def health():
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return {'status': 'ok', 'provider': settings.executor}

    app.include_router(router)
    app.include_router(accounts_router)
    return app


app = create_app()
