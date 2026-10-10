import { useState } from 'react';
import { Link } from 'react-router-dom';
import Login from './Login';
import Register from './Register';

/**
 * Default entry experience. Unauthenticated visitors land here first:
 * a gallery atelier with a Sign In / Create Account switch reusing the
 * full Login and Register pages (identical logic, no duplicate code),
 * plus a quiet door to public event browsing.
 */
export default function AuthEntry() {
  const [mode, setMode] = useState('signin');

  return (
    <div className="page">
      <div className="auth-entry">
        <aside className="auth-entry__panel" aria-hidden="true">
          <p className="auth-entry__kicker">EventFlow · The programme</p>
          <h2>
            An elegant evening,
            <br />
            <em>beautifully booked.</em>
          </h2>
          <p>
            Concerts, conferences and gatherings — curated, rated by real attendees, and scanned at the door
            with tickets that admit exactly once.
          </p>
          <dl className="auth-entry__facts">
            <div>
              <dt>Entry</dt>
              <dd>QR door scanning</dd>
            </div>
            <div>
              <dt>Trust</dt>
              <dd>Verified accounts</dd>
            </div>
            <div>
              <dt>Support</dt>
              <dd>Human help desk</dd>
            </div>
          </dl>
        </aside>
        <section className="auth-entry__forms" aria-label="Sign in or create account">
          <div className="auth-switch" role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signin'}
              className={`auth-switch__tab ${mode === 'signin' ? 'is-active' : ''}`}
              onClick={() => setMode('signin')}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signup'}
              className={`auth-switch__tab ${mode === 'signup' ? 'is-active' : ''}`}
              onClick={() => setMode('signup')}
            >
              Create Account
            </button>
          </div>
          <div key={mode} className="auth-entry__pane">
            {mode === 'signin' ? <Login embedded /> : <Register embedded />}
          </div>
          <p className="muted auth-entry__browse">
            Just looking? <Link to="/browse">Continue browsing events</Link>
          </p>
        </section>
      </div>
    </div>
  );
}
