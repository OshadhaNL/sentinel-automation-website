import { useState } from 'react';
import Icon from '../../components/common/Icon.jsx';
import { formatDate } from '../../data/dashboard.js';

export default function TesterManagement({ testers, onCreate }) {
  const [search, setSearch] = useState('');
  const filtered = testers.filter((tester) => (tester.name + ' ' + tester.email).toLowerCase().includes(search.trim().toLowerCase()));
  return (
    <section className="panel tester-management-panel">
      <div className="panel-heading"><div><h2>Tester accounts <span className="account-count">{testers.length}</span></h2><p className="tester-table-description">Create and view the testers in your demo workspace.</p></div><button className="primary-button" onClick={onCreate}><Icon name="userPlus" size={18} />Create Tester</button></div>
      <div className="tester-search"><label htmlFor="tester-search">Search testers</label><input id="tester-search" type="search" placeholder="Search by name or email" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
      {!testers.length ? <div className="tester-empty"><span className="login-mark"><Icon name="users" size={30} /></span><h3>No testers yet</h3><p>Create your first tester account to get started.</p><button className="text-button" onClick={onCreate}>Create your first tester</button></div>
        : !filtered.length ? <div className="empty-state"><h3>No matching testers</h3><p>Try another name or email address.</p></div>
        : <div className="table-scroll" tabIndex={0} role="region" aria-label="Tester accounts"><table className="testers-table"><thead><tr><th>Tester</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th></tr></thead><tbody>{filtered.map((tester) => <tr key={tester.id}><td><span className="tester-name"><span className="tester-avatar">{tester.initials}</span>{tester.name}</span></td><td>{tester.email}</td><td>Tester</td><td><span className="status-badge status-passed">Active</span></td><td><time dateTime={tester.createdAt}>{formatDate(tester.createdAt)}</time></td></tr>)}</tbody></table></div>}
      <p className="tester-persistence-note"><Icon name="sample" size={16} />Created accounts are cleared on reload. The built-in demo tester remains available. Use demo credentials only.</p>
    </section>
  );
}
