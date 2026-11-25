from datetime import timedelta
import secrets


from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from app.core.security import admin_only, current_user, hash_password, token_hash, user_profile, verify_password
from app.db.database import get_db, utc, utcnow
from app.models import AuditEvent, Invitation, LoginSession, User
from app.schemas import AcceptInvitationInput, AccountStatusInput, InviteInput, OutlookTesterInput, PasswordChangeInput
from app.services.account_security import audit, validate_password
from app.services.mail import send_invitation
from app.services.outlook_draft import prepare_welcome_email

router = APIRouter(prefix='/api')


def throttle(request, limit=10):
    import time
    key = (request.url.path, request.client.host if request.client else 'unknown')
    now = time.monotonic()
    with request.app.state.login_lock:
        attempts = request.app.state.login_attempts
        for entry in list(attempts):
            attempts[entry] = [value for value in attempts[entry] if now - value < 60]
            if not attempts[entry]:
                del attempts[entry]
        if len(attempts.get(key, [])) >= limit:
            raise HTTPException(429, 'Too many attempts. Try again in a minute.')
        attempts.setdefault(key, []).append(now)


def create_invitation(db, request, user, actor):
    now = utcnow()
    db.execute(update(Invitation).where(Invitation.user_id == user.id, Invitation.used_at.is_(None)).values(used_at=now))
    token = secrets.token_urlsafe(32)
    db.add(Invitation(token_hash=token_hash(token), user_id=user.id, expires_at=now + timedelta(hours=24)))
    try:
        delivery = send_invitation(request.app.state.settings, user.email, token)
    except Exception as error:
        db.rollback()
        raise HTTPException(503, 'Invitation delivery failed. Check the email configuration and try again.') from error
    audit(db, 'tester_invited', actor, user)
    db.commit()
    messages = {'outbox': 'Invitation saved to the local development outbox; no email was sent.',
                'smtp': 'Invitation sent.', 'graph': 'Microsoft accepted the invitation email for delivery.'}
    return dict(**user_profile(user), delivery=delivery, message=messages[delivery])


@router.post('/testers/outlook-draft', status_code=201)
def create_outlook_tester(data: OutlookTesterInput, request: Request, actor=Depends(admin_only), db=Depends(get_db)):
    throttle(request)
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise HTTPException(409, 'An account with this email already exists.')
    user = User(name=data.name, email=data.email, designation=data.designation, role='tester', password_hash='')
    db.add(user)
    try:
        db.flush()
        return prepare_welcome_email(db, request.app.state.settings, user, actor, 'tester_outlook_draft_created')
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, 'An account with this email already exists.') from error


@router.post('/testers/{user_id}/outlook-draft')
def reissue_outlook_draft(user_id: str, request: Request, actor=Depends(admin_only), db=Depends(get_db)):
    throttle(request, 5)
    user = db.scalar(select(User).where(User.id == user_id, User.role == 'tester').with_for_update())
    if not user:
        raise HTTPException(404, 'Tester not found.')
    pending_invite = user.invited and not user.email_verified_at
    if not pending_invite and (not user.is_active or not user.must_change_password):
        raise HTTPException(409, 'Welcome drafts are available only for pending invitations or accounts awaiting their first password change.')
    return prepare_welcome_email(db, request.app.state.settings, user, actor, 'tester_outlook_draft_reissued')


@router.post('/testers', status_code=201)
def invite_tester(data: InviteInput, request: Request, actor=Depends(admin_only), db=Depends(get_db)):
    throttle(request)
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise HTTPException(409, 'An account with this email already exists.')
    user = User(name=data.name, email=data.email, role='tester', is_active=False, invited=True,
                password_hash=hash_password(secrets.token_urlsafe(40)))
    db.add(user)
    db.flush()
    return create_invitation(db, request, user, actor)


@router.post('/testers/{user_id}/invite')
def resend_invitation(user_id: str, request: Request, actor=Depends(admin_only), db=Depends(get_db)):
    throttle(request, 5)
    user = db.scalar(select(User).where(User.id == user_id, User.role == 'tester').with_for_update())
    if not user:
        raise HTTPException(404, 'Tester not found.')
    if not user.invited or user.email_verified_at:
        raise HTTPException(409, 'Only pending invitations can be resent.')
    return create_invitation(db, request, user, actor)


@router.post('/auth/invitations/accept')
def accept_invitation(data: AcceptInvitationInput, request: Request, db=Depends(get_db)):
    throttle(request)
    try:
        validate_password(data.password)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    invitation = db.get(Invitation, token_hash(data.token))
    if not invitation or invitation.used_at or utc(invitation.expires_at) <= utcnow():
        raise HTTPException(400, 'This invitation is invalid, expired, or already used. Ask your admin to resend it.')
    user = db.scalar(select(User).where(User.id == invitation.user_id).with_for_update())
    invitation = db.scalar(select(Invitation).where(Invitation.token_hash == token_hash(data.token))
                           .with_for_update().execution_options(populate_existing=True))
    if invitation.used_at or utc(invitation.expires_at) <= utcnow():
        raise HTTPException(400, 'This invitation is invalid, expired, or already used. Ask your admin to resend it.')
    invitation.used_at = utcnow()
    user.password_hash = hash_password(data.password)
    user.email_verified_at = utcnow()
    user.must_change_password = False
    user.is_active = True
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    audit(db, 'invitation_accepted', user, user)
    db.commit()
    return {'message': 'Email verified and account activated. You can now sign in.'}


@router.post('/testers/{user_id}/status')
def set_status(user_id: str, data: AccountStatusInput, actor=Depends(admin_only), db=Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id, User.role == 'tester').with_for_update())
    if not user:
        raise HTTPException(404, 'Tester not found.')
    if data.is_active and user.invited and not user.email_verified_at:
        raise HTTPException(409, 'The tester must accept their invitation first.')
    user.is_active = data.is_active
    if not data.is_active:
        db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
        db.execute(update(Invitation).where(Invitation.user_id == user.id, Invitation.used_at.is_(None)).values(used_at=utcnow()))
    audit(db, 'tester_enabled' if data.is_active else 'tester_disabled', actor, user)
    db.commit()
    return user_profile(user)


@router.post('/auth/password')
def change_password(data: PasswordChangeInput, request: Request, response: Response, account=Depends(current_user), db=Depends(get_db)):
    throttle(request)
    user = db.scalar(select(User).where(User.id == account.id).with_for_update())
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, 'Current password is incorrect.')
    try:
        validate_password(data.password)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if verify_password(data.password, user.password_hash):
        raise HTTPException(422, 'Choose a different password.')
    user.password_hash = hash_password(data.password)
    user.must_change_password = False
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=utcnow() + timedelta(hours=8)))
    audit(db, 'password_changed', user, user)
    db.commit()
    response.set_cookie('sentinel_session', token, httponly=True, secure=request.app.state.settings.secure_cookies,
                        samesite='strict', max_age=8 * 3600, path='/')
    return user_profile(user)


@router.get('/audit')
def audit_history(page: int = Query(1, ge=1), actor=Depends(admin_only), db=Depends(get_db)):
    events = list(db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).offset((page - 1) * 30).limit(30)))
    users = {user.id: user for user in db.scalars(select(User))}
    return dict(total=db.scalar(select(func.count()).select_from(AuditEvent)), page=page,
                items=[dict(id=event.id, action=event.action, createdAt=utc(event.created_at).isoformat(),
                            actor=users[event.actor_id].name if event.actor_id in users else 'Unknown',
                            target=users[event.target_id].name if event.target_id in users else '—') for event in events])
