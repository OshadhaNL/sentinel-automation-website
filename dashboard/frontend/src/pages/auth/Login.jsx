import { useState } from 'react';
import Icon from '../../components/common/Icon.jsx';
import { login } from '../../services/api.js';
import { version as appVersion } from '../../../package.json';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError('');
    try { onLogin(await login(email, password)); }
    catch (failure) { setError(failure.message); }
    finally { setSubmitting(false); }
  }

  return <main className="simple-login-page">
    <section className="simple-login-card" aria-labelledby="login-title">
      <header className="simple-login-header">
        <div className="simple-login-wordmark"><span className="simple-login-logo"><Icon name="shield" size={25} /></span><div>Northlark<span>Sentinel Automation</span></div></div>
      </header>
      <div className="simple-login-content">
        <div className="simple-login-form-panel">
        <div className="simple-login-intro"><h1 id="login-title">Sign in</h1><p>Access your testing workspace.</p></div>
        <form onSubmit={handleSubmit} className="simple-login-form" aria-label="Sign in">
          <div className="form-field">
            <label htmlFor="email">Email address</label>
            <input id="email" name="email" type="email" autoComplete="username" placeholder="you@northlark.com" required
              value={email} onChange={(event) => { setEmail(event.target.value); setError(''); }}
              aria-describedby={error ? 'login-error' : undefined} aria-invalid={Boolean(error)} />
          </div>
          <div className="form-field">
            <label htmlFor="password">Password</label>
            <div className="password-field">
              <input id="password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required
                value={password} onChange={(event) => { setPassword(event.target.value); setError(''); }}
                aria-describedby={error ? 'login-error' : undefined} aria-invalid={Boolean(error)} />
              <button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>
                <Icon name={showPassword ? 'eyeOff' : 'eye'} size={19} />
              </button>
            </div>
          </div>
          {error && <p id="login-error" className="form-error" role="alert">{error}</p>}
          <button className="primary-button simple-login-submit" type="submit" disabled={submitting}><span>{submitting ? 'Signing in...' : 'Sign in'}</span>{!submitting && <Icon name="chevronRight" size={19} />}</button>
        </form>
        </div>
        <div className="simple-login-brand">
          <span className="simple-login-product-mark"><Icon name="shield" size={48} /></span>
          <h2>Sentinel</h2>
          <p>Test Automation Framework</p>
          <span className="simple-login-stack">Python + Playwright</span>
        </div>
      </div>
      <footer className="simple-login-footer"><span>© {new Date().getFullYear()} Northlark</span><span className="simple-login-version">Version {appVersion}</span></footer>
    </section>
  </main>;
}
