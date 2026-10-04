import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function VerifyEmail() {
  const { verifyEmail, resendVerification } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [email, setEmail] = useState(params.get('email') || '');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
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
    setError('');
    setInfo('');
    try {
      const data = await resendVerification(email.trim().toLowerCase());
      setInfo(data.detail || 'Code sent.');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page page--narrow">
      <h1>Verify your email</h1>
      <p className="muted">Enter the 6-digit code we sent to your inbox (expires in 15 minutes).</p>
      <form className="form" onSubmit={handleSubmit}>
        <label>
          Email
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Verification code
          <input
            required
            inputMode="numeric"
            maxLength={6}
            placeholder="123456"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        {info && <p className="form-ok">{info}</p>}
        <button className="btn btn--primary" type="submit" disabled={submitting}>
          {submitting ? 'Verifying…' : 'Verify account'}
        </button>
        <button type="button" className="btn btn--ghost" onClick={handleResend}>
          Resend code
        </button>
      </form>
      <p className="muted">
        <Link to="/login">Back to login</Link>
      </p>
    </div>
  );
}
