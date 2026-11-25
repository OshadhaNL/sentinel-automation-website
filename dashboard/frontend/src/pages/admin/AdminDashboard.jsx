import Dashboard from '../tester/Dashboard.jsx';
import Icon from '../../components/common/Icon.jsx';

export default function AdminDashboard(props) {
  return (
    <>
      <div className="admin-access-note">
        <span className="admin-access-icon"><Icon name="shield" size={22} /></span>
        <div><strong>Tester administration</strong><p>Manage tester accounts, welcome emails, and access from Tester Management.</p></div>
        <button className="primary-button admin-create-tester" onClick={() => props.onNavigate('testers')}><Icon name="users" size={18} />Manage Testers</button>
      </div>
      <Dashboard {...props} />
      <section className="panel admin-summary-panel" aria-label="Administration overview">
        <div className="admin-summary-item"><span className="admin-summary-icon"><Icon name="layers" /></span><div><h2>System coverage</h2><p><strong>{props.modules.length} modules</strong> in the test inventory</p></div></div>
        <div className="admin-summary-item"><span className="admin-summary-icon"><Icon name="reports" /></span><div><h2>Execution review</h2><p>Browse recent runs and inspect their results.</p></div></div>
        <div className="admin-summary-item"><span className="admin-summary-icon"><Icon name="users" /></span><div><h2>Tester accounts</h2><p><strong>{props.testerCount} testers</strong> in this workspace.</p><button className="text-button admin-manage-link" onClick={() => props.onNavigate('testers')}>Manage testers</button></div></div>
      </section>
    </>
  );
}
