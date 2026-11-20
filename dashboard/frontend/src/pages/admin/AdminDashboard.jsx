import Dashboard from '../tester/Dashboard.jsx';
import Icon from '../../components/common/Icon.jsx';

export default function AdminDashboard(props) {
  return (
    <>
      <div className="admin-access-note">
        <span className="admin-access-icon"><Icon name="shield" size={22} /></span>
        <div><strong>Administrator workspace</strong><p>Review test coverage, execution history, and reports across all modules.</p></div>
        <button className="primary-button admin-create-tester" onClick={props.onCreateTester}><Icon name="userPlus" size={18} />Create Tester</button>
      </div>
      <Dashboard {...props} />
      <section className="panel admin-summary-panel" aria-label="Administration overview">
        <div className="admin-summary-item"><span className="admin-summary-icon"><Icon name="layers" /></span><div><h2>System coverage</h2><p><strong>{props.modules.length} modules</strong> in the sample inventory</p></div></div>
        <div className="admin-summary-item"><span className="admin-summary-icon"><Icon name="reports" /></span><div><h2>Execution review</h2><p>Browse recent runs and inspect sample results.</p></div></div>
        <div className="admin-summary-item"><span className="admin-summary-icon"><Icon name="users" /></span><div><h2>Tester accounts</h2><p><strong>{props.testerCount} active testers</strong> in this demo workspace.</p><button className="text-button admin-manage-link" onClick={() => props.onNavigate('testers')}>Manage testers</button></div></div>
      </section>
    </>
  );
}
