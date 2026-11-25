"""Create tables and explicitly provision initial accounts from environment variables."""
import os

from sqlalchemy import select

from app.core.config import Settings
from app.core.security import ADMIN_EMAIL, hash_password
from app.db.database import Base, make_database
from app.db.migrations import upgrade_schema
from app.models import User
from app.schemas import TesterInput
from app.services.account_security import validate_password


def provision(db, name, email, password, role):
    data = TesterInput(name=name, email=email, password=password)
    if role == 'admin' and data.email != ADMIN_EMAIL:
        raise ValueError('Only admin@northlark.com can be provisioned as an administrator.')
    existing = db.scalar(select(User).where(User.email == data.email))
    if existing:
        if existing.role != role:
            raise ValueError(f'Existing account has a different role: {data.email}')
        return existing
    user = User(name=data.name, email=data.email, role=role, password_hash=hash_password(data.password))
    try:
        validate_password(data.password)
    except ValueError:
        user.must_change_password = True
    db.add(user)
    db.commit()
    return user


def main():
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')
    if not admin_email or not admin_password:
        raise SystemExit('Set ADMIN_EMAIL and ADMIN_PASSWORD in dashboard/.env before setup.')
    engine, sessions = make_database(Settings())
    Base.metadata.create_all(engine)
    upgrade_schema(engine)
    with sessions() as db:
        provision(db, 'Northlark Admin', admin_email, admin_password, 'admin')
        if os.getenv('TESTER_EMAIL') and os.getenv('TESTER_PASSWORD'):
            provision(db, 'Northlark Tester', os.environ['TESTER_EMAIL'], os.environ['TESTER_PASSWORD'], 'tester')
    engine.dispose()
    print('Database ready. Initial accounts provisioned; existing passwords were not reset.')


if __name__ == '__main__':
    main()
