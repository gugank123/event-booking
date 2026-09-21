import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, totalRemaining } from '../utils/format';

export default function OrganizerDashboard() {
  const { token } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  function load() {
    setLoading(true);
    api
      .get('/events/?mine=true', token)
      .then((data) => setEvents(data.events))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [token]);

  async function handleCancel(id) {
    if (!window.confirm('Cancel this event? Attendees will keep their bookings, but the event will be marked cancelled.')) return;
    try {
      await api.put(`/events/${id}/`, { status: 'cancelled' }, token);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Your events</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link className="btn btn--ghost" to="/messages">
            Customer messages
          </Link>
          <Link className="btn btn--primary" to="/organizer/new">
            Create event
          </Link>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <p className="muted">Loading…</p>
      ) : events.length === 0 ? (
        <p className="muted">You haven't created any events yet.</p>
      ) : (
        <div className="organizer-list">
          {events.map((e) => (
            <div key={e.id} className="organizer-row">
              <div>
                <span className={`status-pill status-pill--${e.status}`}>{e.status}</span>
                <h3>{e.title}</h3>
                <p className="muted">
                  {formatDate(e.starts_at)} · {e.venue}, {e.city}
                </p>
              </div>
              <div className="organizer-row__stats">
                <span>{totalRemaining(e.ticket_types)} tickets left</span>
              </div>
              <div className="organizer-row__actions">
                <Link className="btn btn--ghost" to={`/organizer/events/${e.id}`}>
                  Attendees & sales
                </Link>
                {e.status !== 'cancelled' && (
                  <button className="btn btn--ghost" onClick={() => handleCancel(e.id)}>
                    Cancel event
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
