import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api, imageSrc } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney, totalRemaining } from '../utils/format';

function eventStats(e) {
  const sold = e.tickets_sold || 0;
  const left = totalRemaining(e.ticket_types);
  const revenue = (e.ticket_types || []).reduce(
    (sum, t) => sum + Number(t.price) * (t.quantity_sold || 0),
    0
  );
  return { sold, left, revenue, orders: e.bookings_count || 0 };
}

export default function OrganizerDashboard() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [totals, setTotals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);

  function load() {
    setLoading(true);
    Promise.all([
      api.get('/events/?mine=true&page_size=50', token),
      api.get('/events/organizer/dashboard/', token).catch(() => null)
    ])
      .then(([data, dash]) => {
        setEvents(data.events);
        if (dash) setTotals(dash.totals);
        setError('');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [token]);

  async function setStatus(id, status, confirmMsg) {
    if (confirmMsg && !window.confirm(confirmMsg)) return;
    setBusyId(id);
    try {
      await api.put(`/events/${id}/`, { status }, token);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleDuplicate(id) {
    setBusyId(id);
    try {
      const data = await api.post(`/events/${id}/duplicate/`, {}, token);
      navigate(`/organizer/events/${data.event.id}/edit`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id, title) {
    if (!window.confirm(`Delete the draft "${title}"? This cannot be undone.`)) return;
    setBusyId(id);
    try {
      await api.del(`/events/${id}/`, token);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>My events</h1>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="btn btn--ghost" to="/messages">
            Customer messages
          </Link>
          <Link className="btn btn--primary" to="/organizer/new">
            ＋ Post event
          </Link>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}
      {totals && (
        <div className="stat-grid" style={{ marginBottom: '1rem' }}>
          <div className="stat-card"><span>Events</span><strong>{totals.events}</strong></div>
          <div className="stat-card"><span>Published</span><strong>{totals.published}</strong></div>
          <div className="stat-card"><span>Tickets sold</span><strong>{totals.tickets_sold}</strong></div>
          <div className="stat-card"><span>Revenue</span><strong>{formatMoney(totals.revenue)}</strong></div>
          <div className="stat-card"><span>Refunds / cancels</span><strong>{totals.refunds}</strong></div>
        </div>
      )}
      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <h3>No events yet.</h3>
          <p>Post your first event to start selling tickets.</p>
          <Link className="btn btn--primary" to="/organizer/new" style={{ marginTop: '1rem' }}>
            ＋ Post event
          </Link>
        </div>
      ) : (
        <div className="organizer-list">
          {events.map((e, i) => {
            const s = eventStats(e);
            return (
              <motion.div
                key={e.id}
                className="organizer-row organizer-row--rich"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: Math.min(i * 0.05, 0.4) }}
              >
                {imageSrc(e.display_image || e.image_url) && (
                  <img className="organizer-row__thumb" src={imageSrc(e.display_image || e.image_url)} alt="" />
                )}
                <div className="organizer-row__main">
                  <span className={`status-pill status-pill--${e.status === 'published' ? 'published' : e.status === 'draft' ? 'draft' : 'cancelled'}`}>
                    {e.status}
                  </span>
                  <h3>{e.title}</h3>
                  <p className="muted">
                    {formatDate(e.starts_at)} · {e.venue}, {e.city}
                  </p>
                  <p className="organizer-row__numbers">
                    {s.sold} sold · {s.left} left · {s.orders} orders · {formatMoney(s.revenue)}
                  </p>
                </div>
                <div className="organizer-row__actions">
                  <Link className="btn btn--ghost btn--sm" to={`/events/${e.id}`}>
                    View
                  </Link>
                  <Link className="btn btn--ghost btn--sm" to={`/organizer/events/${e.id}/edit`}>
                    Edit
                  </Link>
                  <Link className="btn btn--ghost btn--sm" to={`/organizer/events/${e.id}/preview`}>
                    Preview
                  </Link>
                  <Link className="btn btn--ghost btn--sm" to={`/organizer/events/${e.id}`}>
                    Sales
                  </Link>
                  {e.status === 'draft' && (
                    <button className="btn btn--primary btn--sm" disabled={busyId === e.id} onClick={() => setStatus(e.id, 'published')}>
                      Publish
                    </button>
                  )}
                  {e.status === 'published' && (
                    <button className="btn btn--ghost btn--sm" disabled={busyId === e.id} onClick={() => setStatus(e.id, 'draft', 'Unpublish this event? It will disappear from public listings.')}>
                      Unpublish
                    </button>
                  )}
                  {e.status !== 'cancelled' && e.status !== 'completed' && (
                    <button className="btn btn--ghost btn--sm" disabled={busyId === e.id} onClick={() => setStatus(e.id, 'cancelled', 'Cancel this event? Confirmed attendees will be notified automatically.')}>
                      Cancel
                    </button>
                  )}
                  <button className="btn btn--ghost btn--sm" disabled={busyId === e.id} onClick={() => handleDuplicate(e.id)}>
                    Duplicate
                  </button>
                  {e.status === 'draft' && (
                    <button className="btn btn--danger btn--sm" disabled={busyId === e.id} onClick={() => handleDelete(e.id, e.title)}>
                      Delete
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
