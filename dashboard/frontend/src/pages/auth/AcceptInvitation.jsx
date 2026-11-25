import { useState } from 'react';
import { acceptInvitation } from '../../services/api.js';

export default function AcceptInvitation({ token, onDone }) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setBusy(true); setError('');
    try { const result = await acceptInvitation(token, password); setMessage(result.message); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <main className="security-page"><section className="security-card"><h1>Accept your invitation</h1>
    {message ? <><p role="status">{message}</p><button className="primary-button" onClick={onDone}>Go to sign in</button></> : <form onSubmit={submit}>
      <p>Set a unique passphrase of 6–128 characters to verify your email and activate your tester account.</p>
      <div className="form-field"><label htmlFor="new-password">Password</label><input id="new-password" type="password" autoComplete="new-password" minLength={6} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} /></div>
      <div className="form-field"><label htmlFor="confirm-password">Confirm password</label><input id="confirm-password" type="password" autoComplete="new-password" required value={confirm} onChange={(event) => setConfirm(event.target.value)} /></div>
      {error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={busy}>{busy ? 'Activating...' : 'Activate account'}</button>
    </form>}
  </section></main>;
}
