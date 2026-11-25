import { useState } from 'react';
import OutlookDraft from './OutlookDraft.jsx';

export default function CreateTesterForm({ onCreate, onCancel }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [designation, setDesignation] = useState('');
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault();
    if (saving) return;
    const normalized = email.trim().toLowerCase();
    if (!/^[^\s@]+@northlark\.com$/.test(normalized)) { setError('Only @northlark.com email addresses are allowed.'); return; }
    setSaving(true); setError('');
    try { const result = await onCreate({ name, email: normalized, designation }); setDraft(result.emailDraft); }
    catch (failure) { setError(failure.message); setSaving(false); }
  }
  if (draft) return <OutlookDraft draft={draft} onClose={onCancel} />;
  return <form className="create-tester-form" onSubmit={submit}>
    <p className="tester-form-note">Create a tester account with a random temporary password, then review and send the welcome email from Outlook.</p>
    <fieldset disabled={saving}>
      <div className="form-field"><label htmlFor="tester-name">Full name</label><input id="tester-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={100} required /></div>
      <div className="form-field"><label htmlFor="tester-email">Company email</label><input id="tester-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="tester@northlark.com" maxLength={254} required /><small className="field-help">Only @northlark.com addresses are allowed.</small></div>
      <div className="form-field"><label htmlFor="tester-designation">Designation</label><input id="tester-designation" value={designation} onChange={(event) => setDesignation(event.target.value)} placeholder="e.g. QA Engineer" minLength={2} maxLength={100} required /></div>
    </fieldset>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="form-actions"><button className="secondary-button" type="button" onClick={onCancel} disabled={saving}>Cancel</button><button className="primary-button" disabled={saving}>{saving ? 'Creating...' : 'Create account & preview email'}</button></div>
  </form>;
}
