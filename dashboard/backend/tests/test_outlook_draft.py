import re

from sqlalchemy import func, select

from app.core.security import verify_password
from app.models import AuditEvent, User
from conftest import login


DETAILS = {'name': 'Jane Tester', 'email': 'jane@northlark.com', 'designation': 'QA Engineer'}


def temporary_password(response):
    return re.search(r'Temporary password: (\S+)', response.json()['emailDraft']['body']).group(1)


def test_outlook_draft_without_email_service_and_first_login_password_change(api, monkeypatch):
    client, app = api
    login(client, 'admin')
    app.state.settings.mail_mode = 'graph'
    app.state.settings.microsoft_client_secret = ''
    def unexpected_send(*args, **kwargs):
        raise AssertionError('Manual Outlook draft must not send email or use a provider.')
    monkeypatch.setattr('app.api.routes.accounts.send_invitation', unexpected_send)
    response = client.post('/api/testers/outlook-draft', json=DETAILS)
    assert response.status_code == 201, response.text
    result = response.json()
    password = temporary_password(response)
    assert len(password) >= 6
    assert result['designation'] == 'QA Engineer'
    assert result['mustChangePassword'] and result['isActive']
    assert not result['invitationPending']
    assert result['emailDraft']['to'] == DETAILS['email']
    assert 'Hi Jane Tester,' in result['emailDraft']['body']
    assert app.state.settings.public_url + '/' in result['emailDraft']['body']
    with app.state.sessions() as db:
        user = db.get(User, result['id'])
        assert verify_password(password, user.password_hash)
        assert user.password_hash != password
        assert user.email_verified_at is None
        assert password not in str(client.get('/api/audit').json())
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == 'tester_outlook_draft_created')) == 1
    listed = client.get('/api/testers')
    assert password not in listed.text and 'emailDraft' not in listed.text
    assert not (app.state.settings.reports_root.parent / 'email_outbox').exists()
    assert client.post('/api/auth/login', json={'email': DETAILS['email'], 'password': password}).status_code == 200
    assert client.get('/api/dashboard').status_code == 403
    assert client.post('/api/auth/password', json={'current_password': password, 'password': 'MyNew6!Password'}).status_code == 200
    assert client.get('/api/dashboard').status_code == 200


def test_draft_permissions_validation_duplicate_and_designation(api):
    client, app = api
    assert client.post('/api/testers/outlook-draft', json=DETAILS).status_code == 401
    login(client)
    assert client.post('/api/testers/outlook-draft', json=DETAILS).status_code == 403
    login(client, 'admin')
    for overrides in ({'email': 'jane@gmail.com'}, {'designation': ' '}, {'designation': 'x' * 101}, {'role': 'admin'}):
        assert client.post('/api/testers/outlook-draft', json={**DETAILS, **overrides}).status_code == 422
    response = client.post('/api/testers/outlook-draft', json={**DETAILS, 'email': ' JANE@NORTHLARK.COM ', 'designation': ' QA Engineer '})
    assert response.status_code == 201
    assert response.json()['email'] == DETAILS['email']
    assert response.json()['designation'] == DETAILS['designation']
    assert client.post('/api/testers/outlook-draft', json=DETAILS).status_code == 409


def test_reissuing_draft_rotates_password_and_revokes_old_sessions(api):
    client, app = api
    login(client, 'admin')
    first = client.post('/api/testers/outlook-draft', json=DETAILS)
    first_password = temporary_password(first)
    user_id = first.json()['id']
    assert client.post('/api/auth/login', json={'email': DETAILS['email'], 'password': first_password}).status_code == 200
    old_cookie = client.cookies.get('sentinel_session')
    login(client, 'admin')
    second = client.post('/api/testers/' + user_id + '/outlook-draft')
    assert second.status_code == 200
    second_password = temporary_password(second)
    assert first_password != second_password
    from app.models import LoginSession
    from app.core.security import token_hash
    with app.state.sessions() as db:
        assert db.get(LoginSession, token_hash(old_cookie)) is None
    assert client.post('/api/auth/login', json={'email': DETAILS['email'], 'password': first_password}).status_code == 401
    assert client.post('/api/auth/login', json={'email': DETAILS['email'], 'password': second_password}).status_code == 200
    assert client.post('/api/auth/password', json={'current_password': second_password, 'password': 'MyNew6!Password'}).status_code == 200
    login(client, 'admin')
    assert client.post('/api/testers/' + user_id + '/outlook-draft').status_code == 409
