import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request

from app.db.database import get_db, utc, utcnow
from app.models import LoginSession, User

ADMIN_EMAIL = 'admin@northlark.com'


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'


def verify_password(password, encoded):
    try:
        algorithm, iterations, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def user_profile(user):
    return dict(id=user.id, name=user.name, email=user.email, designation=user.designation, role=user.role,
                initials=''.join(word[0] for word in user.name.split()[:2]).upper(),
                createdAt=utc(user.created_at).isoformat(), isActive=user.is_active,
                mustChangePassword=user.must_change_password, invitationPending=user.invited and not user.email_verified_at)


def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get('sentinel_session', '')
    session = db.get(LoginSession, token_hash(token)) if token else None
    if not session or utc(session.expires_at) <= utcnow():
        raise HTTPException(401, 'Please sign in.')
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, 'Account is inactive.')
    if user.role == 'admin' and user.email != ADMIN_EMAIL:
        raise HTTPException(403, 'This account is not authorised as an administrator.')
    allowed = {'/api/auth/me', '/api/auth/logout', '/api/auth/password'}
    if request.url.path not in allowed:
        if user.must_change_password:
            raise HTTPException(403, 'Change your password before continuing.')
    return user


def admin_only(user=Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, 'Only admins can manage testers.')
    return user


def tester_only(user=Depends(current_user)):
    if user.role != 'tester':
        raise HTTPException(403, 'Only testers can execute tests.')
    return user
