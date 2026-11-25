"""Password policy and account audit events."""
from app.models import AuditEvent


def validate_password(password):
    common = {'password', 'password123', 'northlark', '123456', 'qwerty', 'admin123', 'letmein', 'welcome',
              'passwordpassword', 'passwordpassword123', '123456789012345',
              '12345678901234567890', 'qwertyuiopasdfgh', 'northlarknorthlark',
              'letmeinletmeinletmein', 'correcthorsebatterystaple'}
    if not 6 <= len(password) <= 128 or password.strip().casefold() in common or len(set(password)) < 5:
        raise ValueError('Use 6–128 characters and avoid common or repeated passwords. A unique passphrase works well.')


def audit(db, action, actor=None, target=None):
    db.add(AuditEvent(action=action, actor_id=actor.id if actor else None, target_id=target.id if target else None))
