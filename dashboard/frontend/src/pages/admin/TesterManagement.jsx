import { useEffect, useState } from 'react';
import { formatDate } from '../../data/dashboard.js';
import { getTesters, prepareOutlookDraft, setTesterStatus } from '../../services/api.js';
import Modal from '../../components/common/Modal.jsx';
import OutlookDraft from '../../components/common/OutlookDraft.jsx';

export default function TesterManagement({ testers, onCreate }) {
  const [accounts, setAccounts] = useState(testers);
  const [search, setSearch] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [draft, setDraft] = useState(null);
  useEffect(() => setAccounts(testers), [testers]);
  const filtered = accounts.filter((tester) => (tester.name + ' ' + tester.email + ' ' + tester.designation).toLowerCase().includes(search.trim().toLowerCase()));
  async function manage(tester, resend = false) {
    setBusy(tester.id); setError(''); setNotice('');
    try {
      const result = resend ? await prepareOutlookDraft(tester.id) : await setTesterStatus(tester.id, !tester.isActive && !tester.invitationPending);
      if (resend) setDraft(result.emailDraft);
      setNotice(resend ? result.message : tester.name + (result.isActive ? ' enabled.' : ' disabled. Existing sessions revoked.'));
      setAccounts(await getTesters());
    } catch (failure) { setError(failure.message); }
    finally { setBusy(''); }
  }
  return <section className="panel tester-management-panel">
    <div className="panel-heading"><div><h2>Tester accounts <span className="account-count">{accounts.length}</span></h2><p className="tester-table-description">Invite testers and manage their access.</p></div><button className="primary-button" onClick={onCreate}>Invite Tester</button></div>
    <div className="tester-search"><label htmlFor="tester-search">Search testers</label><input id="tester-search" type="search" placeholder="Search by name or email" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="panel-note" role="status">{notice}</p>}
    {!filtered.length ? <p className="empty-state">No matching tester accounts.</p> : <div className="table-scroll"><table className="testers-table"><thead><tr><th>Tester</th><th>Email</th><th>Designation</th><th>Status</th><th>Created</th><th>Action</th></tr></thead><tbody>{filtered.map((tester) => <tr key={tester.id}>
      <td>{tester.name}</td><td>{tester.email}</td><td>{tester.designation || '—'}</td><td><span className={tester.isActive ? 'status-badge status-passed' : 'status-badge status-skipped'}>{tester.invitationPending ? 'Invitation pending' : !tester.isActive ? 'Disabled' : tester.mustChangePassword ? 'Temporary password' : 'Active'}</span></td><td>{formatDate(tester.createdAt)}</td>
      <td>{(tester.invitationPending || (tester.isActive && tester.mustChangePassword)) && <button className="text-button" disabled={Boolean(busy)} onClick={() => manage(tester, true)}>Prepare welcome email</button>}<button className="text-button" disabled={Boolean(busy)} onClick={() => manage(tester)}>{busy === tester.id ? 'Saving...' : tester.isActive || tester.invitationPending ? 'Disable' : 'Enable'}</button></td>
    </tr>)}</tbody></table></div>}
    <p className="tester-persistence-note">Disabling an account revokes its sessions and invitations. Its execution history is preserved.</p>
    {draft && <Modal wide title="Welcome email preview" onClose={() => setDraft(null)}><OutlookDraft draft={draft} onClose={() => setDraft(null)} /></Modal>}
  </section>;
}
