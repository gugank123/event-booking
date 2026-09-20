import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney } from '../utils/format';

export default function MyBookings() {
  const { token } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);

  function load() {
    setLoading(true);
    api
      .get('/bookings/mine/', token)
      .then((data) => setBookings(data.bookings))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [token]);

  async function handleCancel(id) {
    if (!window.confirm('Cancel this booking? This can\u2019t be undone.')) return;
    setBusyId(id);
    try {
      await api.post(`/bookings/${id}/cancel/`, {}, token);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page">
      <h1>My tickets</h1>
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <p className="muted">Loading…</p>
      ) : bookings.length === 0 ? (
        <p className="muted">
          No bookings yet. <Link to="/">Browse events</Link> to get started.
        </p>
      ) : (
        <div className="booking-list">
          {bookings.map((b) => (
            <div key={b.id} className={`booking-row ${b.status === 'cancelled' ? 'is-cancelled' : ''}`}>
              <div>
                <h3>{b.event ? b.event.title : 'Event removed'}</h3>
                <p className="muted">
                  {b.event && `${formatDate(b.event.startsAt)} · ${b.event.venue}, ${b.event.city}`}
                </p>
                <p className="booking-row__ref">Ref {b.reference}</p>
              </div>
              <div className="booking-row__details">
                <span>{b.quantity} × {b.ticketTypeName}</span>
                <span>{formatMoney(b.totalAmount)}</span>
                <span className={`status-pill status-pill--${b.status}`}>{b.status}</span>
              </div>
              {b.status === 'confirmed' && (
                <button className="btn btn--ghost" disabled={busyId === b.id} onClick={() => handleCancel(b.id)}>
                  {busyId === b.id ? 'Cancelling…' : 'Cancel'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
