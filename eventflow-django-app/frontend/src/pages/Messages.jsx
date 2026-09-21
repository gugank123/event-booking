import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils/format';

export default function Messages() {
  const { user, token } = useAuth();
  const [convs, setConvs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get('/comms/conversations/mine/', token)
      .then((data) => setConvs(data.conversations))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]);

  const isOrganizer = user?.role === 'organizer' || user?.role === 'admin';

  return (
    <div className="page">
      <h1>{isOrganizer ? 'Customer messages' : 'My messages'}</h1>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : convs.length === 0 ? (
        <div className="empty-state">
          <h3>No conversations yet.</h3>
          <p>
            {isOrganizer
              ? 'Customer enquiries about your events will appear here.'
              : 'Use Contact Organizer on any event page to start one.'}
          </p>
        </div>
      ) : (
        <div className="conversation-list">
          {convs.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i * 0.04, 0.3) }}
            >
              <Link to={`/messages/${c.id}`} className="conversation-row">
                <div>
                  <h3>
                    #{c.id} · {c.subject}
                  </h3>
                  <p className="muted">
                    {isOrganizer ? c.customer_name : c.organizer_name}
                    {c.event_title ? ` · ${c.event_title}` : ''} · {formatDate(c.updated_at)}
                  </p>
                </div>
                <div className="conversation-row__meta">
                  {c.unread_count > 0 && <span className="bell__badge">{c.unread_count}</span>}
                  <span className={`status-pill status-pill--${c.status === 'OPEN' ? 'published' : c.status === 'CLOSED' || c.status === 'RESOLVED' ? 'cancelled' : 'draft'}`}>
                    {c.status.replace('_', ' ')}
                  </span>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
