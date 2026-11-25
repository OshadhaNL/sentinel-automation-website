"""Small additive updates for existing dashboard databases."""
from sqlalchemy import inspect, text


def upgrade_schema(engine):
    columns = {column['name'] for column in inspect(engine).get_columns('test_runs')}
    if 'workers' not in columns:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE test_runs ADD COLUMN workers INTEGER NOT NULL DEFAULT 1'))
    with engine.begin() as connection:
        if 'browser' not in columns:
            connection.execute(text("ALTER TABLE test_runs ADD COLUMN browser VARCHAR(20) NOT NULL DEFAULT 'chromium'"))
        if 'batch_id' not in columns:
            connection.execute(text('ALTER TABLE test_runs ADD COLUMN batch_id VARCHAR(36)'))
    additions = {
        'users': {
            'designation': "VARCHAR(100) NOT NULL DEFAULT ''",
            'must_change_password': 'BOOLEAN NOT NULL DEFAULT true',
            'invited': 'BOOLEAN NOT NULL DEFAULT false',
            'email_verified_at': 'TIMESTAMP WITH TIME ZONE',
            'mfa_secret': 'TEXT', 'mfa_pending_secret': 'TEXT',
            'mfa_pending_expires': 'TIMESTAMP WITH TIME ZONE',
            'mfa_last_step': 'INTEGER NOT NULL DEFAULT -1',
            'recovery_hashes': "JSON NOT NULL DEFAULT '[]'",
        },
        'login_sessions': {'mfa_verified': 'BOOLEAN NOT NULL DEFAULT false'},
    }
    for table, fields in additions.items():
        if not inspect(engine).has_table(table):
            continue
        existing = {column['name'] for column in inspect(engine).get_columns(table)}
        with engine.begin() as connection:
            for name, definition in fields.items():
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
