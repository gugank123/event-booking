import { Link } from 'react-router-dom';
import { Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

/** Public entry for posting events. Organizers go straight through;
 *  everyone else learns how to get an organizer account. */
export default function PostEvent() {
  const { user, loading } = useAuth();

  if (loading) return <div className="page">Loading…</div>;
  if (user?.role === 'organizer' || user?.role === 'admin') {
    return <Navigate to="/organizer/new" replace />;
  }

  return (
    <div className="page page--narrow">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <span className="ticket-card__category">For organisers</span>
        <h1>Post your event</h1>
        <p className="muted">
          Publishing events needs an <strong>organizer</strong> account (attendees can only book).
          {user
            ? ' You are signed in as an attendee — register a separate organizer account to continue.'
            : ' Create a free organizer account, then come back here.'}
        </p>
        <div className="help-cards" style={{ marginTop: '1.5rem' }}>
          <Link to="/register" className="help-card">
            <h3>＋ Register as organizer</h3>
            <p>Choose “Create and sell events” on the signup form. Takes a minute.</p>
          </Link>
          {!user && (
            <Link to="/login" className="help-card">
              <h3>Log in</h3>
              <p>Already have an organizer account? Sign in with it.</p>
            </Link>
          )}
          {user && (
            <Link to="/" className="help-card">
              <h3>🎟 Book instead</h3>
              <p>Stay as an attendee and browse events to book.</p>
            </Link>
          )}
        </div>
        <p className="muted" style={{ marginTop: '1.5rem' }}>
          Demo organizer login: <code>organizer@eventflow.dev</code> / <code>password123</code>
        </p>
      </motion.div>
    </div>
  );
}
