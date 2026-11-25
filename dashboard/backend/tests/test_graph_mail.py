import re
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import select

from app.core.security import token_hash
from app.models import Invitation, User
from conftest import login


def configure_graph(app):
    settings = app.state.settings
    settings.mail_mode = 'graph'
    settings.microsoft_tenant_id = '11111111-1111-1111-1111-111111111111'
    settings.microsoft_client_id = '22222222-2222-2222-2222-222222222222'
    settings.microsoft_client_secret = 'test-client-secret&value+!'
    settings.mail_from = 'sender@northlark.com'
    return settings


def mock_graph(monkeypatch, handler):
    original_client = httpx.Client
    monkeypatch.setattr('app.services.mail.httpx.Client',
                        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs))


def test_graph_invitation_oauth_and_accepted_message(api, monkeypatch):
    client, app = api
    login(client, 'admin')
    settings = configure_graph(app)
    requests = []
    body = {}
    def handler(request):
        requests.append(request)
        if request.url.host == 'login.microsoftonline.com':
            assert request.url.path == '/' + settings.microsoft_tenant_id + '/oauth2/v2.0/token'
            form = parse_qs(request.content.decode())
            assert form['client_secret'] == [settings.microsoft_client_secret]
            assert form['grant_type'] == ['client_credentials']
            assert form['scope'] == ['https://graph.microsoft.com/.default']
            return httpx.Response(200, json={'access_token': 'test-access-token'})
        assert str(request.url) == 'https://graph.microsoft.com/v1.0/users/sender%40northlark.com/sendMail'
        assert request.headers['authorization'] == 'Bearer test-access-token'
        import json
        body.update(json.loads(request.content))
        return httpx.Response(202)
    mock_graph(monkeypatch, handler)
    response = client.post('/api/testers', json={'name': 'Graph Tester', 'email': 'graph@northlark.com'})
    assert response.status_code == 201, response.text
    assert response.json()['delivery'] == 'graph'
    assert 'accepted' in response.json()['message']
    assert len(requests) == 2
    assert body['message']['toRecipients'] == [{'emailAddress': {'address': 'graph@northlark.com'}}]
    token = re.search(r'#invite=([A-Za-z0-9_-]+)', body['message']['body']['content']).group(1)
    assert token not in response.text
    assert settings.microsoft_client_secret not in response.text
    with app.state.sessions() as db:
        assert db.get(Invitation, token_hash(token)) is not None
    assert not (settings.reports_root.parent / 'email_outbox').exists()


@pytest.mark.parametrize('stage,status', [('token', 401), ('send', 403), ('send', 429), ('missing_token', 200)])
def test_graph_failure_rolls_back_invitation_without_fallback(api, monkeypatch, stage, status):
    client, app = api
    login(client, 'admin')
    settings = configure_graph(app)
    def handler(request):
        if request.url.host == 'login.microsoftonline.com':
            if stage == 'token':
                return httpx.Response(status, json={'error': 'unauthorized_client'})
            return httpx.Response(200, json={} if stage == 'missing_token' else {'access_token': 'test-access-token'})
        return httpx.Response(status, json={'error': 'provider rejected the send'})
    mock_graph(monkeypatch, handler)
    response = client.post('/api/testers', json={'name': 'Graph Tester', 'email': 'graph@northlark.com'})
    assert response.status_code == 503
    assert 'test-access-token' not in response.text and settings.microsoft_client_secret not in response.text
    with app.state.sessions() as db:
        assert db.scalar(select(User).where(User.email == 'graph@northlark.com')) is None
    assert not (settings.reports_root.parent / 'email_outbox').exists()


def test_graph_without_credentials_does_not_attempt_network(api, monkeypatch):
    client, app = api
    login(client, 'admin')
    settings = configure_graph(app)
    settings.microsoft_client_secret = ''
    def unexpected_request(request):
        pytest.fail('A network request was attempted without configuration.')
    mock_graph(monkeypatch, unexpected_request)
    response = client.post('/api/testers', json={'name': 'Graph Tester', 'email': 'graph@northlark.com'})
    assert response.status_code == 503
