from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def utcnow():
    return datetime.now(timezone.utc)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class Base(DeclarativeBase):
    pass


def make_database(settings):
    settings.validate()
    url = settings.database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    options = {'check_same_thread': False} if url.startswith('sqlite') else {'connect_timeout': 5}
    engine = create_engine(url, connect_args=options, pool_pre_ping=True)
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def enable_foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine, sessionmaker(engine, expire_on_commit=False)


def get_db(request: Request):
    with request.app.state.sessions() as db:
        yield db
