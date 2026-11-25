import { useState, useEffect, useRef } from 'react';
import Icon from '../common/Icon.jsx';

export default function Header({ onToggleSidebar, user, onLogout, onSecurity }) {
  const [open, setOpen] = useState(null);
  const actions = useRef(null);

  useEffect(() => {
    function dismiss(event) {
      if (event.type === 'keydown' ? event.key === 'Escape' : !actions.current?.contains(event.target)) setOpen(null);
    }
    document.addEventListener('pointerdown', dismiss);
    document.addEventListener('keydown', dismiss);
    return () => {
      document.removeEventListener('pointerdown', dismiss);
      document.removeEventListener('keydown', dismiss);
    };
  }, []);

  return (
    <header className="app-header">
      <div className="brand">
        <button className="icon-button mobile-menu" aria-label="Toggle navigation" onClick={onToggleSidebar}><Icon name="menu" /></button>
        <Icon name="shield" size={43} />
        <span>Sentinel Automation Dashboard</span>
      </div>
      <div className="header-actions" ref={actions}>
        <span className="role-pill"><span className="role-dot" />{user.role === 'admin' ? 'Admin' : 'Tester'}</span>
        <div className="popover-anchor">
          <button className="icon-button notification-button" aria-label="Notifications" aria-expanded={open === 'notifications'}
            onClick={() => setOpen(open === 'notifications' ? null : 'notifications')}><Icon name="bell" size={27} /></button>
          {open === 'notifications' && <section className="header-popover"><h2>Notifications</h2><p>You're all caught up.</p><small>Live notifications are unavailable in this frontend preview.</small></section>}
        </div>
        <div className="popover-anchor">
          <button className="profile-button" aria-label="Account menu" aria-expanded={open === 'profile'}
            onClick={() => setOpen(open === 'profile' ? null : 'profile')}>
            <span className="avatar">{user.initials}</span><Icon name="chevronDown" size={20} />
          </button>
          {open === 'profile' && <section className="header-popover profile-popover"><h2>{user.name}</h2><p>{user.email}</p><small>{user.role === 'admin' ? 'Administrator' : 'Tester'}</small><button className="sign-out-button" onClick={onSecurity}>Change password</button><button className="sign-out-button" onClick={onLogout}><Icon name="logout" size={18} />Sign out</button></section>}
        </div>
      </div>
    </header>
  );
}
