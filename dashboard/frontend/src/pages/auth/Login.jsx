import { useState } from 'react';
import Icon from '../../components/common/Icon.jsx';
import { signInDemo, createTesterPreview } from '../../services/demoAuth.js';

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
    try {
      onLogin(await signInDemo(email, password));
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-brand-panel" aria-label="Sentinel Automation">
        <div className="login-brand"><Icon name="shield" size={38} /><span>Sentinel<span className="login-brand-caption">AUTOMATION DASHBOARD</span></span></div>
        <div className="login-intro">
          <span className="login-eyebrow">QUALITY. CLARITY. CONFIDENCE.</span>
          <h1>Your tests.<br />One clear view.</h1>
          <p>Keep track of test coverage, review executions, and turn results into a clearer picture of quality.</p>
          <div className="login-feature"><Icon name="layers" size={22} /><span>Every module, connected.</span></div>
          <div className="login-feature"><Icon name="reports" size={22} /><span>Results you can act on.</span></div>
        </div>
        <span className="login-brand-footer">Sentinel Automation · Northlark</span>
        <Icon name="shield" size={390} className="login-watermark" />
      </section>
      <section className="login-form-panel" aria-label="Sign in">
        <div className="login-card">
          <span className="login-mark"><Icon name="shield" size={29} /></span>
          <h2>Welcome back</h2>
          <p className="login-description">Sign in to your Sentinel workspace.</p>
          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-field">
              <label htmlFor="email">Email address</label>
              <input id="email" name="email" type="email" autoComplete="username" placeholder="you@northlark.com" required
                value={email} onChange={(event) => { setEmail(event.target.value); setError(''); }} aria-describedby={error ? 'login-error' : undefined} aria-invalid={Boolean(error)} />
            </div>
            <div className="form-field">
              <label htmlFor="password">Password</label>
              <div className="password-field">
                <input id="password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" required
                  value={password} onChange={(event) => { setPassword(event.target.value); setError(''); }} aria-describedby={error ? 'login-error' : undefined} aria-invalid={Boolean(error)} />
                <button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>
                  <Icon name={showPassword ? 'eyeOff' : 'eye'} size={20} />
                </button>
              </div>
            </div>
            {error && <p id="login-error" className="form-error" role="alert"><Icon name="alert" size={18} />{error}</p>}
            <button className="primary-button login-submit" type="submit" disabled={submitting}>{submitting ? 'Signing in…' : 'Sign in'}</button>
          </form>
          <div className="login-demo-note"><Icon name="sample" size={18} /><p><strong>Frontend demo</strong>Sign in with the supplied admin or tester credentials, or a tester created in this tab. Reloading clears created accounts. No live authentication is connected.</p></div>
          <button className="tester-preview-button" type="button" onClick={() => onLogin(createTesterPreview())}>Explore tester preview</button>
        </div>
        <p className="login-footer">Sentinel Automation Dashboard</p>
      </section>
    </main>
  );
}
