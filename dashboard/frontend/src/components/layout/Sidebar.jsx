import Icon from '../common/Icon.jsx';
import { modules } from '../../data/dashboard.js';

export default function Sidebar({ view, onNavigate, open, onClose, user }) {
  const links = [
    { id: 'overview', label: 'Dashboard', icon: 'home' },
    { id: 'all', label: 'All Systems', icon: 'layers' },
    ...modules.map((module) => ({ id: module.name, label: module.name, icon: module.icon })),
    { id: 'reports', label: 'Reports', icon: 'reports' },
    ...(user.role === 'admin' ? [{ id: 'testers', label: 'Testers', icon: 'users' }] : []),
  ];
  return (
    <>
      {open && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={onClose} />}
      <aside className={'sidebar' + (open ? ' sidebar-open' : '')}>
        <nav aria-label="Main navigation">
          {links.map((link) => (
            <button key={link.id} className={'nav-item' + (view === link.id ? ' active' : '')}
              aria-current={view === link.id ? 'page' : undefined}
              onClick={() => { onNavigate(link.id); onClose(); }}>
              <Icon name={link.icon} size={25} /><span>{link.label}</span>
            </button>
          ))}
        </nav>
      </aside>
    </>
  );
}
