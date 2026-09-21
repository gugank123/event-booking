import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils/format';

export default function Invitations() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    api
      .get('/comms/invitations/mine/', token)
      .then((data) => setInvites(data.invitations))
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(load, [token]);

  async function respond(invToken, action) {
    try {
      await api.post(`/comms/invitations/${invToken}/${action}/`, {}, token);
      if (action === 'accept') {
        const inv = invites.find((i) => i.token === invToken);
        navigate(`/events/${inv.event}`);
      } else {
        load();
      }
    } catch {
      load();
    }
  }

  return (
    <div className="page">
      <h1>Invitations</h1>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : invites.length === 0 ? (
        <div className="empty-state">
          <h3>No invitations.</h3>
          <p>When organisers invite you to events, they'll show up here.</p>
        </div>
      ) : (
        <div className="invite-grid">
          {invites.map((inv, i) => (
            <motion.div
              key={inv.id}
              className="invite-card"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: Math.min(i * 0.05, 0.4) }}
            >
              <span className="ticket-card__category">Invitation</span>
              <h3>{inv.event_title}</h3>
              {inv.message && <p className="muted">“{inv.message}”</p>}
              <p className="muted">Invited {formatDate(inv.created_at)}</p>
              <span className={`status-pill status-pill--${inv.status === 'ACCEPTED' ? 'published' : inv.status === 'PENDING' ? 'draft' : 'cancelled'}`}>
                {inv.status}
              </span>
              {inv.status === 'PENDING' && (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                  <button className="btn btn--primary btn--sm" onClick={() => respond(inv.token, 'accept')}>
                    Accept & view event
                  </button>
                  <button className="btn btn--ghost btn--sm" onClick={() => respond(inv.token, 'decline')}>
                    Decline
                  </button>
                </div>
              )}
              {inv.status !== 'PENDING' && (
                <div style={{ marginTop: '0.75rem' }}>
                  <Link className="btn btn--ghost btn--sm" to={`/events/${inv.event}`}>
                    View event
                  </Link>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
