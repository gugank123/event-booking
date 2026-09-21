import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils/format';
import { refreshNotifications } from '../components/NotificationBell';

const CATEGORY_LABEL = {
  BOOKING: 'Booking',
  EVENT: 'Event',
  INVITATION: 'Invitation',
  MESSAGE: 'Message',
  PAYMENT: 'Payment',
  SUPPORT: 'Support',
  SYSTEM: 'System'
};

export default function Notifications() {
  const { token } = useAuth();
  const [notes, setNotes] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    const params = new URLSearchParams();
    if (filter === 'unread') params.set('unread', 'true');
    api
      .get(`/comms/notifications/${params.toString() ? `?${params}` : ''}`, token)
      .then((data) => setNotes(data.notifications))
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(load, [token, filter]);

  async function markRead(id) {
    await api.post(`/comms/notifications/${id}/read/`, {}, token).catch(() => {});
    setNotes((ns) => ns.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    refreshNotifications();
  }

  async function markAllRead() {
    await api.post('/comms/notifications/read-all/', {}, token).catch(() => {});
    setNotes((ns) => ns.map((n) => ({ ...n, is_read: true })));
    refreshNotifications();
  }

  async function remove(id) {
    await api.del(`/comms/notifications/${id}/`, token).catch(() => {});
    setNotes((ns) => ns.filter((n) => n.id !== id));
    refreshNotifications();
  }

  return (
    <div className="page page--narrow">
      <div className="page-header">
        <h1>Notifications</h1>
        <button className="btn btn--ghost btn--sm" onClick={markAllRead}>
          Mark all read
        </button>
      </div>
      <div className="filter-row">
        {['all', 'unread'].map((f) => (
          <button key={f} className={`chip ${filter === f ? 'is-active' : ''}`} onClick={() => setFilter(f)}>
            {f === 'all' ? 'All' : 'Unread'}
          </button>
        ))}
      </div>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : notes.length === 0 ? (
        <div className="empty-state">
          <h3>All caught up.</h3>
          <p>No notifications here.</p>
        </div>
      ) : (
        <div className="notification-list">
          {notes.map((n, i) => (
            <motion.div
              key={n.id}
              className={`notification ${n.is_read ? '' : 'is-unread'}`}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i * 0.04, 0.3) }}
            >
              <div>
                <span className="notification__category">{CATEGORY_LABEL[n.category] || n.category}</span>
                <h4>{n.title}</h4>
                <p>{n.message}</p>
                <span className="muted">{formatDate(n.created_at)}</span>{' '}
                {n.link && <Link to={n.link}>View →</Link>}
              </div>
              <div className="notification__actions">
                {!n.is_read && (
                  <button className="btn btn--ghost btn--sm" onClick={() => markRead(n.id)}>
                    Mark read
                  </button>
                )}
                <button className="btn btn--ghost btn--sm" onClick={() => remove(n.id)}>
                  Delete
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
