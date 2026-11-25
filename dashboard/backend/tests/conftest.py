from pathlib import Path
from email import policy
from email.parser import BytesParser
import re



import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.setup import provision

TEST_PASSWORD = 'A unique Sentinel passphrase 2026!'


@pytest.fixture
def api(tmp_path):
    metadata = tmp_path / 'metadata.json'
    metadata.write_text('{}', encoding='utf-8')
    settings = Settings(database_url='sqlite:///' + (tmp_path / 'test.db').as_posix(), testing=True,
                        reports_root=tmp_path / 'reports', metadata_file=metadata, executor='mock', mail_mode='outbox')
    app = create_app(settings)
    with TestClient(app) as client:
        with app.state.sessions() as db:
            provision(db, 'Admin', 'admin@northlark.com', TEST_PASSWORD, 'admin')
            provision(db, 'Tester', 'tester@northlark.com', TEST_PASSWORD, 'tester')
        yield client, app


def login(client, role='tester'):
    response = client.post('/api/auth/login', json={'email': f'{role}@northlark.com', 'password': TEST_PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()

def invitation_token(app):
    folder = app.state.settings.reports_root.parent / 'email_outbox'
    path = max(folder.glob('*.eml'), key=lambda value: value.stat().st_mtime_ns)
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    return re.search(r'#invite=([A-Za-z0-9_-]+)', message.get_content()).group(1)
