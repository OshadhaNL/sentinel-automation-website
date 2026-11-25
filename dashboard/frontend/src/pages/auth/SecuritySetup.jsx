import { useState } from 'react';
import { changePassword } from '../../services/api.js';

export default function SecuritySetup({ onComplete, onLogout }) {
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function updatePassword(event) {
    event.preventDefault();
    if (busy) return;
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setBusy(true); setError('');
    try { onComplete(await changePassword(current, password)); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <main className="security-page"><section className="security-card"><h1>Update your password</h1>
    <form onSubmit={updatePassword}>
      <p>Choose a password of 6–128 characters.</p>
      <div className="form-field"><label htmlFor="current-password">Current password</label><input id="current-password" type="password" autoComplete="current-password" required value={current} onChange={(event) => setCurrent(event.target.value)} /></div>
      <div className="form-field"><label htmlFor="strong-password">New password</label><input id="strong-password" type="password" autoComplete="new-password" minLength={6} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} /></div>
      <div className="form-field"><label htmlFor="confirm-strong-password">Confirm new password</label><input id="confirm-strong-password" type="password" autoComplete="new-password" required value={confirm} onChange={(event) => setConfirm(event.target.value)} /></div>
      <button className="primary-button" disabled={busy}>Update password</button>
    </form>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="text-button" onClick={onLogout} disabled={busy}>Sign out</button>
  </section></main>;
}
