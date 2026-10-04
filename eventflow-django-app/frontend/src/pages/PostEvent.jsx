import { Link, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

const STEPS = [
  { n: '1', title: 'Create your organizer account', text: 'Register free and choose “Create and sell events”. It takes about a minute.' },
  { n: '2', title: 'Post your event', text: 'Add title, venue, dates, ticket types and a cover image — with a live preview as you type.' },
  { n: '3', title: 'Sell & manage', text: 'Track bookings, scan QR tickets at the door, message attendees and send announcements.' }
];

const PERKS = [
  { icon: '🎟', title: 'Ticketing built in', text: 'Multiple ticket tiers, live availability, QR door entry and check-in.' },
  { icon: '💬', title: 'Talk to attendees', text: 'Announcements, broadcasts and 1-to-1 conversations with your crowd.' },
  { icon: '📊', title: 'Know your numbers', text: 'Revenue, tickets sold, attendee rosters and check-in stats per event.' },
  { icon: '⭐', title: 'Ratings & discovery', text: 'Reviews, wishlist saves, featured spotlights and trending boosts.' },
  { icon: '📩', title: 'Invitations', text: 'Invite guests by email with a shareable link and track responses.' },
  { icon: '🔔', title: 'Auto-notifications', text: 'Date or venue changes notify every confirmed attendee for you.' }
];

export default function PostEvent() {
  const { user, loading } = useAuth();

  if (loading) return <div className="page">Loading…</div>;
  if (user?.role === 'organizer' || user?.role === 'admin') {
    return <Navigate to="/organizer/new" replace />;
  }

  return (
    <div className="page">
      <section className="hero">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55 }}
        >
          <span className="ticket-card__category">For organisers</span>
          <h1>
            Your event, <em>sold out.</em>
          </h1>
          <p>
            Post your event on EventFlow and reach people looking for a night out —
            with ticketing, messaging and door check-in included.
          </p>
          <div className="hero__cta">
            <Link className="btn btn--primary" to="/register">
              ＋ Register as organizer
            </Link>
            {!user && (
              <Link className="btn btn--ghost" to="/login">
                Log in
              </Link>
            )}
          </div>
        </motion.div>
      </section>

      <div className="section-head">
        <h2>How it works</h2>
      </div>
      <div className="steps-grid">
        {STEPS.map((s, i) => (
          <motion.div
            key={s.n}
            className="step-card"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.1 }}
          >
            <span className="step-card__num">{s.n}</span>
            <h3>{s.title}</h3>
            <p className="muted">{s.text}</p>
          </motion.div>
        ))}
      </div>

      <div className="section-head">
        <h2>Everything included</h2>
      </div>
      <div className="perks-grid">
        {PERKS.map((p, i) => (
          <motion.div
            key={p.title}
            className="help-card"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 + i * 0.06 }}
          >
            <h3>
              {p.icon} {p.title}
            </h3>
            <p>{p.text}</p>
          </motion.div>
        ))}
      </div>

      <motion.section
        className="cta-banner"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.2 }}
      >
        <div>
          <h2>Ready when you are.</h2>
          <p className="muted">
            {user
              ? 'You are signed in as an attendee — register a separate organizer account to post.'
              : 'Free to start. Post your first event in minutes.'}
          </p>
        </div>
        <div className="cta-banner__actions">
          <Link className="btn btn--primary" to="/register">
            Get started
          </Link>
          <Link className="btn btn--ghost" to="/">
            Browse events
          </Link>
        </div>
      </motion.section>

      <p className="muted" style={{ marginTop: '1.5rem' }}>
        Demo organizer login: <code>organizer@eventflow.dev</code> / <code>password123</code>
      </p>
    </div>
  );
}
