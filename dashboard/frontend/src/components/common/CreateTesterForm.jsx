import { useState } from 'react';
import Icon from './Icon.jsx';

export default function CreateTesterForm({ onCreate, onCancel }) {
  const [values, setValues] = useState({ name: '', email: '', password: '', confirmPassword: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  function update(event) {
    setValues({ ...values, [event.target.name]: event.target.value });
    setError('');
  }

  async function submit(event) {
    event.preventDefault();
    if (saving) return;
    if (values.password !== values.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setError('');
    setSaving(true);
    try {
      await onCreate({ name: values.name, email: values.email, password: values.password });
    } catch (failure) {
      setError(failure.message);
      setSaving(false);
    }
  }

  return (
    <form className="create-tester-form" onSubmit={submit} aria-busy={saving}>
      <p className="tester-form-note">Create a tester account with access to test execution and reports.</p>
      <fieldset disabled={saving}>
        <div className="form-field"><label htmlFor="tester-name">Full name</label><input id="tester-name" name="name" autoComplete="name" placeholder="Enter tester's full name" value={values.name} onChange={update} required minLength={2} maxLength={100} /></div>
        <div className="form-field"><label htmlFor="tester-email">Email address</label><input id="tester-email" name="email" type="email" autoComplete="off" placeholder="tester@northlark.com" value={values.email} onChange={update} required maxLength={254} /></div>
        <div className="form-field"><label htmlFor="tester-password">Password</label><div className="password-field"><input id="tester-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="At least 8 characters" value={values.password} onChange={update} required minLength={8} aria-describedby="tester-password-help" /><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide passwords' : 'Show passwords'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}><Icon name={showPassword ? 'eyeOff' : 'eye'} size={20} /></button></div><small id="tester-password-help" className="field-help">Use a password with at least 8 characters.</small></div>
        <div className="form-field"><label htmlFor="tester-confirm-password">Confirm password</label><input id="tester-confirm-password" name="confirmPassword" type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="Re-enter password" value={values.confirmPassword} onChange={update} required minLength={8} /></div>
      </fieldset>
      <div className="tester-role-note"><Icon name="profiles" size={18} /><span>Role: <strong>Tester</strong> · Active account</span></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><button className="secondary-button" type="button" onClick={onCancel} disabled={saving}>Cancel</button><button className="primary-button" type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create Tester'}</button></div>
    </form>
  );
}
