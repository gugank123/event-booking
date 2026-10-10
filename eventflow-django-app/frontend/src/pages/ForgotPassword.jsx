import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ForgotPassword() {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await forgotPassword(email.trim().toLowerCase());
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page page--narrow">
      <div className="auth-wrap">
        <p className="auth-kicker">Lost your key</p>
        <h1>Forgot password</h1>
        {done ? (
          <>
            <p className="form-ok">
              If an account exists for that email, a reset link is on its way (valid 30 minutes, single use).
            </p>
            <nav className="auth-links" aria-label="Account help">
              <Link to="/login">Back to login</Link>
            </nav>
          </>
        ) : (
          <>
            <p className="auth-lede">Tell us the email on your account and we&apos;ll send a secure reset link.</p>
            <form className="form auth-card" onSubmit={handleSubmit}>
              <label>
                Account email
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
                {submitting ? 'Sending…' : 'Send reset link'}
              </button>
            </form>
            <nav className="auth-links" aria-label="Account help">
              <Link to="/login">Back to login</Link>
            </nav>
          </>
        )}
      </div>
    </div>
  );
}
