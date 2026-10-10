import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GoogleSignInButton from '../components/GoogleSignInButton';

export default function Login({ embedded = false }) {
  const { login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(location.state?.from || '/');
    } catch (err) {
      if (/verify your email/i.test(err.message)) {
        navigate(`/verify-email?email=${encodeURIComponent(email)}`);
        return;
      }
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogle(idToken, googleError) {
    if (googleError) {
      setError(googleError);
      return;
    }
    if (!idToken) return;
    setError('');
    setSubmitting(true);
    try {
      await loginWithGoogle(idToken);
      navigate(location.state?.from || '/');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const outerClass = embedded ? undefined : 'page page--narrow';

  return (
    <div className={outerClass}>
      <div className="auth-wrap">
        <p className="auth-kicker">Members&apos; entrance</p>
        <h1>Log in</h1>
        <p className="auth-lede">Welcome back to the programme. Your tickets, wishlist and organiser tools are waiting.</p>
        <GoogleSignInButton onCredential={handleGoogle} text="signin_with" />
        <div className="divider">
          <span>or with email</span>
        </div>
        <form className="form auth-card" onSubmit={handleSubmit} noValidate={false}>
          <label>
            Email
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Password
            <span className="password-field">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="current-password"
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
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
            {submitting ? 'Logging in…' : 'Log in'}
          </button>
        </form>
        <nav className="auth-links" aria-label="Account help">
          <Link to="/forgot-password">Forgot your password?</Link>
          <Link to="/register">New here? Create an account</Link>
        </nav>
      </div>
    </div>
  );
}
