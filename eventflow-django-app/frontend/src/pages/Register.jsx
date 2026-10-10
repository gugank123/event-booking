import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GoogleSignInButton from '../components/GoogleSignInButton';

export default function Register({ embedded = false }) {
  const { register, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState('attendee');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Choose a password of at least 8 characters.');
      return;
    }
    setSubmitting(true);
    try {
      await register(name, email, phone, password, role);
      navigate(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (err) {
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
      // New Google users get the role selected below; existing users keep theirs.
      await loginWithGoogle(idToken, role);
      navigate('/');
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
        <p className="auth-kicker">Join the audience</p>
        <h1>Create an account</h1>
        <p className="auth-lede">
          One account for booking evenings, saving favourites and — if you wish — staging your own.
        </p>
        <GoogleSignInButton onCredential={handleGoogle} text="signup_with" />
        <div className="divider">
          <span>or with email</span>
        </div>
        <form className="form auth-card" onSubmit={handleSubmit}>
          <label>
            Full name
            <input
              type="text"
              required
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
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
            Phone (optional)
            <input
              type="tel"
              autoComplete="tel"
              value={phone}
              placeholder="+91 …"
              onChange={(e) => setPhone(e.target.value)}
            />
          </label>
          <label>
            Password (at least 8 characters)
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
          <fieldset className="role-choice">
            <legend>I&apos;m signing up to…</legend>
            <label className={`role-option ${role === 'attendee' ? 'is-selected' : ''}`}>
              <input type="radio" name="role" value="attendee" checked={role === 'attendee'} onChange={() => setRole('attendee')} />
              Book tickets to events
            </label>
            <label className={`role-option ${role === 'organizer' ? 'is-selected' : ''}`}>
              <input type="radio" name="role" value="organizer" checked={role === 'organizer'} onChange={() => setRole('organizer')} />
              Create and sell events
            </label>
          </fieldset>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>
        <nav className="auth-links" aria-label="Account help">
          <Link to="/login">Already have an account? Log in</Link>
        </nav>
      </div>
    </div>
  );
}
