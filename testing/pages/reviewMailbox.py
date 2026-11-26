"""Read only a configured test inbox; never send mail or mark messages as read."""
from email import policy
from email.parser import BytesParser
import html
import imaplib
import os
import time


def wait_for_invitation(recipient, link, timeout=60):
    host = os.getenv('WORKFLOW_IMAP_HOST')
    user = os.getenv('WORKFLOW_IMAP_USER')
    token = os.getenv('WORKFLOW_IMAP_OAUTH_TOKEN')
    password = os.getenv('WORKFLOW_IMAP_PASSWORD')
    assert host and user and (token or password), 'Configure the dedicated test inbox before enabling email delivery tests.'
    with imaplib.IMAP4_SSL(host) as mailbox:
        if token:
            mailbox.authenticate('XOAUTH2', lambda _: f'user={user}\x01auth=Bearer {token}\x01\x01'.encode())
        else:
            mailbox.login(user, password)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            assert mailbox.select('INBOX', readonly=True)[0] == 'OK'
            status, data = mailbox.search(None, 'TO', '"' + recipient + '"')
            assert status == 'OK'
            for message_id in reversed(data[0].split()[-20:]):
                status, raw = mailbox.fetch(message_id, '(BODY.PEEK[])')
                assert status == 'OK'
                payload = next(part[1] for part in raw if isinstance(part, tuple))
                message = BytesParser(policy=policy.default).parsebytes(payload)
                parts = message.walk() if message.is_multipart() else [message]
                content = '\n'.join(part.get_content() for part in parts if part.get_content_type() in ('text/plain', 'text/html'))
                if link in html.unescape(content):
                    assert message['Subject'], 'Invitation email has no subject.'
                    return
            time.sleep(2)
    raise AssertionError('No invitation containing the exact newly created link arrived in the test inbox.')
