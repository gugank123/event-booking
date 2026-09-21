import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney } from '../utils/format';
import TicketQR from '../components/TicketQR';
import ContactOrganizer from '../components/ContactOrganizer';

export default function MyBookings() {
  const { token } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [qrFor, setQrFor] = useState(null);

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
      <div className="page-header">
        <h1>My tickets</h1>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="btn btn--ghost btn--sm" to="/invitations">
            Invitations
          </Link>
          <Link className="btn btn--ghost btn--sm" to="/messages">
            Messages
          </Link>
          <Link className="btn btn--ghost btn--sm" to="/support">
            Support
          </Link>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      ) : bookings.length === 0 ? (
        <div className="empty-state">
          <h3>No bookings yet.</h3>
          <p>
            <Link to="/">Browse events</Link> to get started.
          </p>
        </div>
      ) : (
        <div className="booking-list">
          {bookings.map((b, i) => (
            <motion.div
              key={b.id}
              className={`booking-row ${b.status === 'cancelled' ? 'is-cancelled' : ''}`}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: Math.min(i * 0.05, 0.4) }}
            >
              <div>
                <h3>{b.event ? b.event.title : 'Event removed'}</h3>
                <p className="muted">
                  {b.event && `${formatDate(b.event.startsAt)} · ${b.event.venue}, ${b.event.city}`}
                </p>
                <p className="booking-row__ref">Ref {b.reference}</p>
              </div>
              <div className="booking-row__details">
                <span>
                  {b.quantity} × {b.ticketTypeName}
                </span>
                <span>{formatMoney(b.totalAmount)}</span>
                <span className={`status-pill status-pill--${b.status}`}>{b.status}</span>
                {b.checkedIn && <span className="checkin-pill">Checked in</span>}
              </div>
              <div className="booking-row__qr">
                {b.event && (
                  <ContactOrganizer eventId={b.event.id} bookingId={b.id} eventTitle={b.event.title} />
                )}
                {b.status === 'confirmed' && (
                  <>
                    <button className="btn btn--ghost btn--sm" onClick={() => setQrFor(qrFor === b.id ? null : b.id)}>
                      {qrFor === b.id ? 'Hide QR' : 'Show QR'}
                    </button>
                    <button
                      className="btn btn--ghost btn--sm"
                      disabled={busyId === b.id}
                      onClick={() => handleCancel(b.id)}
                      style={{ marginLeft: '0.5rem' }}
                    >
                      {busyId === b.id ? 'Cancelling…' : 'Cancel'}
                    </button>
                  </>
                )}
              </div>
              {qrFor === b.id && b.status === 'confirmed' && (
                <div style={{ gridColumn: '1 / -1' }}>
                  <p className="muted" style={{ textAlign: 'center' }}>
                    Show this at the door for {b.event ? b.event.title : 'your event'}
                    {b.checkedIn ? ' — already checked in.' : '.'}
                  </p>
                  <TicketQR reference={b.reference} />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
