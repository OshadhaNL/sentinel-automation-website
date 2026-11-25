"""Prepare a welcome email; the admin sends it manually in Outlook."""
import secrets

from sqlalchemy import delete, update

from app.core.security import hash_password, user_profile
from app.db.database import utcnow
from app.models import Invitation, LoginSession
from app.services.account_security import audit, validate_password


def prepare_welcome_email(db, settings, user, actor, action):
    password = secrets.token_urlsafe(12)
    while len(set(password)) < 5:
        password = secrets.token_urlsafe(12)
    validate_password(password)
    user.password_hash = hash_password(password)
    user.must_change_password = True
    user.is_active = True
    user.invited = False
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.execute(update(Invitation).where(Invitation.user_id == user.id, Invitation.used_at.is_(None)).values(used_at=utcnow()))
    audit(db, action, actor, user)
    db.commit()
    subject = 'Your Sentinel tester account has been created'
    body = (f'Hi {user.name},\n\n'
            'Your tester account in the Sentinel Test Automation Framework has been created.\n\n'
            f'Designation: {user.designation}\n'
            f'Email: {user.email}\n'
            f'Temporary password: {password}\n\n'
            f'Sign in here:\n{settings.public_url}/\n\n'
            'You will be asked to change this temporary password before accessing the dashboard.\n\n'
            'Regards,\nNorthlark Sentinel Admin\n')
    # Only the password hash is saved. Draft credentials are returned once to
    # the admin and are never stored in audit events or an email outbox.
    return dict(**user_profile(user), message='Account ready. Open Outlook and click Send there to deliver the email.',
                emailDraft={'to': user.email, 'subject': subject, 'body': body})
