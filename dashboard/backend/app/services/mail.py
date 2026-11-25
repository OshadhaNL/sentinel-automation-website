"""Microsoft Graph, SMTP, or an explicit local development outbox."""
from email.message import EmailMessage
import smtplib
import ssl
import uuid
from urllib.parse import quote

import httpx


def send_graph(settings, recipient, subject, body):
    if not all((settings.microsoft_tenant_id, settings.microsoft_client_id, settings.microsoft_client_secret)):
        raise ValueError('Configure MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, and MICROSOFT_CLIENT_SECRET.')
    # Tenant-specific credentials only; never send secrets to a configurable URL.
    tenant = str(uuid.UUID(settings.microsoft_tenant_id))
    client_id = str(uuid.UUID(settings.microsoft_client_id))
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        authentication = client.post(
            f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
            data={'client_id': client_id, 'client_secret': settings.microsoft_client_secret,
                  'grant_type': 'client_credentials', 'scope': 'https://graph.microsoft.com/.default'})
        authentication.raise_for_status()
        access_token = authentication.json().get('access_token')
        if not access_token:
            raise ValueError('Microsoft did not return an access token.')
        sent = client.post(
            'https://graph.microsoft.com/v1.0/users/' + quote(settings.mail_from, safe='') + '/sendMail',
            headers={'Authorization': 'Bearer ' + access_token},
            json={'message': {'subject': subject, 'body': {'contentType': 'Text', 'content': body},
                              'toRecipients': [{'emailAddress': {'address': recipient}}]}})
        sent.raise_for_status()
        if sent.status_code != 202:
            raise ValueError('Microsoft did not accept the message for delivery.')
    return 'graph'


def send_invitation(settings, recipient, token):
    message = EmailMessage()
    message['From'] = settings.mail_from
    message['To'] = recipient
    message['Subject'] = 'Your Northlark Sentinel invitation'
    link = settings.public_url + '/#invite=' + token
    message.set_content('You have been invited to Sentinel. Set your password and verify your email using this link:\n\n'
                        + link + '\n\nThis single-use invitation expires in 24 hours. If you did not expect it, ignore it.')
    if settings.mail_mode == 'graph':
        return send_graph(settings, recipient, str(message['Subject']), message.get_content())
    if settings.mail_mode == 'outbox':
        folder = settings.reports_root.parent / 'email_outbox'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (uuid.uuid4().hex + '.eml')).write_bytes(message.as_bytes())
        return 'outbox'
    if not settings.smtp_host:
        raise ValueError('Configure SMTP_HOST before sending invitations.')
    client = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
    options = {'context': ssl.create_default_context()} if settings.smtp_ssl else {}
    with client(settings.smtp_host, settings.smtp_port, timeout=20, **options) as server:
        if not settings.smtp_ssl:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
    return 'smtp'
