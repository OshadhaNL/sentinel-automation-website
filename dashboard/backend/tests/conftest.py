from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.setup import provision


@pytest.fixture
def api(tmp_path):
    metadata = tmp_path / 'metadata.json'
    metadata.write_text('{}', encoding='utf-8')
    settings = Settings(database_url='sqlite:///' + (tmp_path / 'test.db').as_posix(), testing=True,
                        reports_root=tmp_path / 'reports', metadata_file=metadata, executor='mock')
    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.sessions() as db:
            provision(db, 'Admin', 'admin@northlark.com', 'password123', 'admin')
            provision(db, 'Tester', 'tester@northlark.com', 'password123', 'tester')
        yield client, app


def login(client, role='tester'):
    response = client.post('/api/auth/login', json={'email': f'{role}@northlark.com', 'password': 'password123'})
    assert response.status_code == 200, response.text
    return response.json()
