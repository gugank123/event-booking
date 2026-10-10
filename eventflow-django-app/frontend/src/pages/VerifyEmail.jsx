import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const RESEND_COOLDOWN_SECONDS = 60;

export default function VerifyEmail() {
  const { verifyEmail, resendVerification } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [email, setEmail] = useState(params.get('email') || '');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (code.trim().length !== 6) {
      setError('Enter the 6-digit code from your email.');
      return;
    }
    setSubmitting(true);
    try {
      await verifyEmail(email.trim().toLowerCase(), code.trim());
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResend() {
    if (cooldown > 0 || resending) return;
    setError('');
    setInfo('');
    setResending(true);
    try {
      const data = await resendVerification(email.trim().toLowerCase());
      setInfo(data.detail || 'A fresh code is on its way.');
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setError(err.message);
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="page page--narrow">
      <div className="auth-wrap">
        <p className="auth-kicker">One last step</p>
        <h1>Verify your email</h1>
        <p className="auth-lede">
          We posted a 6-digit code to your inbox. It expires in 15 minutes — enter it below to open your account.
        </p>
        <form className="form auth-card" onSubmit={handleSubmit}>
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
            Verification code
            <input
              className="code-input"
              required
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="123456"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          {info && <p className="form-ok">{info}</p>}
          <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
            {submitting ? 'Verifying…' : 'Verify account'}
          </button>
          <div className="resend-row">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={handleResend}
              disabled={resending || cooldown > 0}
            >
              {resending ? 'Sending…' : 'Resend code'}
            </button>
            {cooldown > 0 && (
              <span className="cooldown-note" aria-live="polite">
                You may request a new code in {cooldown}s.
              </span>
            )}
          </div>
        </form>
        <nav className="auth-links" aria-label="Account help">
          <Link to="/login">Back to login</Link>
        </nav>
      </div>
    </div>
  );
}
