import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.models import User
from app.schemas import TesterInput
from app.setup import provision
from conftest import login


@pytest.mark.parametrize('email', [
    'tester@gmail.com',
    'tester@sub.northlark.com',
    'tester@northlark.com.evil.com',
    'northlark.com@evil.com',
    'tester@notnorthlark.com',
    'tester@northlark.co',
    'tester@@northlark.com',
    'tester@northlark.com.',
])
def test_admin_cannot_create_external_or_lookalike_email(api, email):
    client, app = api
    login(client, 'admin')
    response = client.post('/api/testers', json={'name': 'Tester', 'email': email})
    assert response.status_code == 422
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 2


def test_company_email_normalized_and_duplicate_rejected(api):
    client, app = api
    login(client, 'admin')
    data = {'name': 'QA Tester', 'email': ' QA.NEW@NORTHLARK.COM '}
    response = client.post('/api/testers', json=data)
    assert response.status_code == 201
    assert response.json()['email'] == 'qa.new@northlark.com'
    data['email'] = 'qa.new@northlark.com'
    assert client.post('/api/testers', json=data).status_code == 409


def test_setup_also_rejects_external_accounts(api):
    client, app = api
    with app.state.sessions() as db:
        with pytest.raises(ValidationError, match='Only @northlark.com'):
            provision(db, 'External Admin', 'admin@example.com', 'test-password', 'admin')
    assert TesterInput(name='QA', email='qa@NORTHLARK.COM', password='test-password').email == 'qa@northlark.com'
