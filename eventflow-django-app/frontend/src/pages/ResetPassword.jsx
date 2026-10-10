import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ResetPassword() {
  const { resetPassword } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [token] = useState(params.get('token') || '');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Choose a password of at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      await resetPassword(token, password, confirm);
      navigate('/login');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div className="page page--narrow">
        <div className="auth-wrap">
          <p className="auth-kicker">Broken seal</p>
          <h1>Reset password</h1>
          <p className="form-error">This reset link is missing its token. Please use the link from your email.</p>
          <nav className="auth-links" aria-label="Account help">
            <Link to="/forgot-password">Request a new link</Link>
          </nav>
        </div>
      </div>
    );
  }

  return (
    <div className="page page--narrow">
      <div className="auth-wrap">
        <p className="auth-kicker">A fresh start</p>
        <h1>Set a new password</h1>
        <p className="auth-lede">Choose something memorable — at least 8 characters. This link works exactly once.</p>
        <form className="form auth-card" onSubmit={handleSubmit}>
          <label>
            New password
            <span className="password-field">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="password-toggle"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword((v) => !v)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </span>
          </label>
          <label>
            Confirm password
            <input
              type={showPassword ? 'text' : 'password'}
              required
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
            {submitting ? 'Updating…' : 'Update password'}
          </button>
        </form>
      </div>
    </div>
  );
}
