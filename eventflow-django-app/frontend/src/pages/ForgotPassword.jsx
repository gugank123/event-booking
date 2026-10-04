import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ForgotPassword() {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await forgotPassword(email.trim().toLowerCase());
      setDone(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page page--narrow">
      <h1>Forgot password</h1>
      {done ? (
        <>
          <p className="form-ok">If an account exists for that email, a reset link was sent (valid 30 minutes).</p>
          <p className="muted">
            <Link to="/login">Back to login</Link>
          </p>
        </>
      ) : (
        <form className="form" onSubmit={handleSubmit}>
          <label>
            Account email
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <button className="btn btn--primary" type="submit" disabled={submitting}>
            {submitting ? 'Sending…' : 'Send reset link'}
          </button>
        </form>
      )}
    </div>
  );
}
