from datetime import timedelta
import secrets

from fastapi.testclient import TestClient

from sqlalchemy import func, select

from app.core.security import hash_password, token_hash
from app.setup import provision
import pytest
from app.db.database import utcnow
from app.models import AuditEvent, Invitation, LoginSession, User
from conftest import invitation_token, login, TEST_PASSWORD


def invite(client, app, email='new@northlark.com'):
    response = client.post('/api/testers', json={'name': 'New Tester', 'email': email})
    assert response.status_code == 201, response.text
    assert response.json()['delivery'] == 'outbox'
    assert not response.json()['isActive']
    return response.json(), invitation_token(app)


def test_invitation_activation_password_policy_expiry_and_replay(api):
    client, app = api
    login(client, 'admin')
    account, token = invite(client, app)
    assert token not in str(account)
    assert client.post('/api/auth/login', json={'email': account['email'], 'password': TEST_PASSWORD}).status_code == 401
    assert client.post('/api/auth/invitations/accept', json={'token': token, 'password': 'passwordpassword'}).status_code == 422
    assert client.post('/api/auth/invitations/accept', json={'token': token, 'password': TEST_PASSWORD}).status_code == 200
    assert client.post('/api/auth/invitations/accept', json={'token': token, 'password': TEST_PASSWORD}).status_code == 400
    with app.state.sessions() as db:
        user = db.get(User, account['id'])
        assert user.is_active and user.email_verified_at and not user.must_change_password
        assert db.get(Invitation, token_hash(token)).used_at
        assert db.get(Invitation, token) is None
    account2, token2 = invite(client, app, 'expired@northlark.com')
    with app.state.sessions() as db:
        db.get(Invitation, token_hash(token2)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post('/api/auth/invitations/accept', json={'token': token2, 'password': TEST_PASSWORD}).status_code == 400


def test_resend_revoke_and_delivery_failure(api, monkeypatch):
    client, app = api
    login(client, 'admin')
    account, first = invite(client, app)
    assert client.post('/api/testers/' + account['id'] + '/status', json={'is_active': True}).status_code == 409
    assert client.post('/api/testers/' + account['id'] + '/invite').status_code == 200
    second = invitation_token(app)
    assert first != second
    assert client.post('/api/auth/invitations/accept', json={'token': first, 'password': TEST_PASSWORD}).status_code == 400
    assert client.post('/api/testers/' + account['id'] + '/status', json={'is_active': False}).status_code == 200
    assert client.post('/api/auth/invitations/accept', json={'token': second, 'password': TEST_PASSWORD}).status_code == 400
    def fail(*args):
        raise OSError('simulated SMTP outage')
    monkeypatch.setattr('app.api.routes.accounts.send_invitation', fail)
    response = client.post('/api/testers', json={'name': 'Failed Delivery', 'email': 'failed@northlark.com'})
    assert response.status_code == 503
    with app.state.sessions() as db:
        assert db.scalar(select(User).where(User.email == 'failed@northlark.com')) is None


def test_deactivation_revokes_sessions_and_preserves_accounts(api):
    client, app = api
    login(client)
    with app.state.sessions() as db:
        tester = db.scalar(select(User).where(User.email == 'tester@northlark.com'))
        target_id = tester.id
        token = secrets.token_urlsafe(32)
        db.add(LoginSession(token_hash=token_hash(token), user_id=target_id, expires_at=utcnow() + timedelta(hours=1)))
        db.commit()
    login(client, 'admin')
    assert client.post('/api/testers/' + target_id + '/status', json={'is_active': False}).status_code == 200
    with app.state.sessions() as db:
        assert not db.get(User, target_id).is_active
        assert db.scalar(select(func.count()).select_from(LoginSession).where(LoginSession.user_id == target_id)) == 0
    assert client.post('/api/auth/login', json={'email': 'tester@northlark.com', 'password': TEST_PASSWORD}).status_code == 401
    assert client.post('/api/testers/' + target_id + '/status', json={'is_active': True}).status_code == 200
    events = client.get('/api/audit').json()['items']
    assert {'tester_disabled', 'tester_enabled'} <= {event['action'] for event in events}
    assert TEST_PASSWORD not in str(events) and token not in str(events)
    login(client)
    assert client.get('/api/audit').status_code == 403
    assert client.post('/api/testers/' + target_id + '/status', json={'is_active': False}).status_code == 403


def test_starter_password_gate_and_change_revokes_old_sessions(api):
    client, app = api
    with app.state.sessions() as db:
        user = db.scalar(select(User).where(User.email == 'tester@northlark.com'))
        user.password_hash = hash_password('password123')
        user.must_change_password = True
        token = secrets.token_urlsafe(32)
        db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=utcnow() + timedelta(hours=1)))
        db.commit()
    response = client.post('/api/auth/login', json={'email': 'tester@northlark.com', 'password': 'password123'})
    assert response.json()['mustChangePassword']
    assert client.get('/api/dashboard').status_code == 403
    assert client.post('/api/auth/password', json={'current_password': 'wrong', 'password': TEST_PASSWORD}).status_code == 400
    assert client.post('/api/auth/password', json={'current_password': 'password123', 'password': '123456789012345'}).status_code == 422
    assert client.post('/api/auth/password', json={'current_password': 'password123', 'password': TEST_PASSWORD}).status_code == 200
    assert client.get('/api/dashboard').status_code == 200
    with app.state.sessions() as db:
        assert db.get(LoginSession, token_hash(token)) is None
    assert client.post('/api/auth/login', json={'email': 'tester@northlark.com', 'password': 'password123'}).status_code == 401


def test_smtp_delivery_uses_tls_and_does_not_use_outbox(api, monkeypatch):
    client, app = api
    login(client, 'admin')
    settings = app.state.settings
    settings.mail_mode = 'smtp'
    settings.smtp_host = 'smtp.example.test'
    settings.smtp_username = 'sender'
    settings.smtp_password = 'smtp-secret'
    calls = []
    class FakeSmtp:
        def __init__(self, host, port, **kwargs):
            calls.append(('connect', host, port))
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self, **kwargs):
            calls.append(('tls',))
        def login(self, username, password):
            calls.append(('login', username, password))
        def send_message(self, message):
            calls.append(('send', message['To']))
    monkeypatch.setattr('app.services.mail.smtplib.SMTP', FakeSmtp)
    response = client.post('/api/testers', json={'name': 'SMTP Tester', 'email': 'smtp@northlark.com'})
    assert response.status_code == 201, response.text
    assert response.json()['delivery'] == 'smtp'
    assert [call[0] for call in calls] == ['connect', 'tls', 'login', 'send']
    assert not (settings.reports_root.parent / 'email_outbox').exists()


def test_six_character_passwords_work_for_activation_and_change(api):
    client, app = api
    login(client, 'admin')
    account, token = invite(client, app)
    assert client.post('/api/auth/invitations/accept', json={'token': token, 'password': 'Ab3!x'}).status_code == 422
    assert client.post('/api/auth/invitations/accept', json={'token': token, 'password': 'Ab3!x9'}).status_code == 200
    assert client.post('/api/auth/login', json={'email': account['email'], 'password': 'Ab3!x9'}).status_code == 200
    assert client.post('/api/auth/password', json={'current_password': 'Ab3!x9', 'password': 'Cd4@y'}).status_code == 422
    assert client.post('/api/auth/password', json={'current_password': 'Ab3!x9', 'password': 'Cd4@y8'}).status_code == 200
    assert client.post('/api/auth/login', json={'email': account['email'], 'password': 'Cd4@y8'}).status_code == 200


def test_admin_signs_in_without_code_even_if_previously_enrolled(api):
    client, app = api
    with app.state.sessions() as db:
        admin = db.scalar(select(User).where(User.email == 'admin@northlark.com'))
        admin.mfa_secret = 'legacy-encrypted-secret'
        db.commit()
    response = client.post('/api/auth/login', json={'email': 'admin@northlark.com', 'password': TEST_PASSWORD})
    assert response.status_code == 200, response.text
    assert 'requiresMfaSetup' not in response.json()
    assert client.get('/api/testers').status_code == 200
    assert client.get('/api/audit').status_code == 200
    assert client.post('/api/auth/mfa/setup').status_code == 404
    assert client.post('/api/auth/mfa/confirm', json={'code': '123456'}).status_code == 404
    assert client.post('/api/auth/login', json={'email': 'admin@northlark.com', 'password': 'wrong'}).status_code == 401


def test_only_fixed_email_can_be_admin_in_setup_login_and_session(api):
    client, app = api
    with app.state.sessions() as db:
        with pytest.raises(ValueError, match='Only admin@northlark.com'):
            provision(db, 'Other Admin', 'other@northlark.com', TEST_PASSWORD, 'admin')
        other = User(name='Other Admin', email='other@northlark.com', role='admin', password_hash=hash_password(TEST_PASSWORD))
        db.add(other)
        db.flush()
        token = secrets.token_urlsafe(32)
        db.add(LoginSession(token_hash=token_hash(token), user_id=other.id, expires_at=utcnow() + timedelta(hours=1)))
        db.commit()
    assert client.post('/api/auth/login', json={'email': 'other@northlark.com', 'password': TEST_PASSWORD}).status_code == 401
    client.cookies.clear()
    client.cookies.set('sentinel_session', token)
    assert client.get('/api/testers').status_code == 403
