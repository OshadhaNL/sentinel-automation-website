"""Small additive updates for existing dashboard databases."""
from sqlalchemy import inspect, text


def upgrade_schema(engine):
    columns = {column['name'] for column in inspect(engine).get_columns('test_runs')}
    if 'workers' not in columns:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE test_runs ADD COLUMN workers INTEGER NOT NULL DEFAULT 1'))
