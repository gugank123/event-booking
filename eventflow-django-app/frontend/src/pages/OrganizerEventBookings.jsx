import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney } from '../utils/format';
import OrganizerComms from '../components/OrganizerComms';

export default function OrganizerEventBookings() {
  const { id } = useParams();
  const { token } = useAuth();
  const [event, setEvent] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [lookupRef, setLookupRef] = useState('');
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupError, setLookupError] = useState('');
  const [checkingId, setCheckingId] = useState(null);

  function load() {
    setLoading(true);
    Promise.all([api.get(`/events/${id}/`), api.get(`/events/${id}/bookings/`, token)])
      .then(([eventData, bookingData]) => {
        setEvent(eventData.event);
        setData(bookingData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [id, token]);

  async function handleLookup(e) {
    e.preventDefault();
    setLookupError('');
    setLookupResult(null);
    if (!lookupRef.trim()) return;
    try {
      const res = await api.get(`/bookings/lookup/?reference=${encodeURIComponent(lookupRef.trim())}`, token);
      setLookupResult(res.booking);
    } catch (err) {
      setLookupError(err.message);
    }
  }

  async function handleCheckIn(bookingId) {
    setCheckingId(bookingId);
    try {
      const res = await api.post(`/bookings/${bookingId}/check-in/`, {}, token);
      setData((prev) => ({
        ...prev,
        bookings: prev.bookings.map((b) => (b.id === bookingId ? res.booking : b))
      }));
      setLookupResult((prev) => (prev && prev.id === bookingId ? res.booking : prev));
    } catch (err) {
      setError(err.message);
    } finally {
      setCheckingId(null);
    }
  }

  if (loading) return <div className="page">Loading…</div>;
  if (error) return <div className="page">{error}</div>;

  const checkedInCount = data.bookings.filter((b) => b.checkedIn && b.status === 'confirmed').length;

  return (
    <div className="page">
      <h1>{event.title}</h1>
      <div className="stat-row">
        <motion.div className="stat-card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
          <span className="stat-card__value">{formatMoney(data.revenue)}</span>
          <span className="stat-card__label">Revenue</span>
        </motion.div>
        <motion.div className="stat-card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>
          <span className="stat-card__value">{data.ticketsSold}</span>
          <span className="stat-card__label">Tickets sold</span>
        </motion.div>
        <motion.div className="stat-card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}>
          <span className="stat-card__value">{checkedInCount}</span>
          <span className="stat-card__label">Checked in</span>
        </motion.div>
        <motion.div className="stat-card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.24 }}>
          <span className="stat-card__value">{data.bookings.length}</span>
          <span className="stat-card__label">Total orders</span>
        </motion.div>
      </div>

      <h2>Door check-in</h2>
      <form className="checkin-box" onSubmit={handleLookup}>
        <input
          placeholder="Ticket reference, e.g. EVF-ABC123"
          value={lookupRef}
          onChange={(e) => setLookupRef(e.target.value)}
        />
        <button className="btn btn--primary btn--sm" type="submit">
          Look up
        </button>
        {lookupError && <span className="form-error">{lookupError}</span>}
        {lookupResult && (
          <span className="muted">
            {lookupResult.attendeeName} · {lookupResult.quantity} × {lookupResult.ticketTypeName} ·
            <span className={`status-pill status-pill--${lookupResult.status}`} style={{ marginLeft: '0.5rem' }}>
              {lookupResult.status}
            </span>
            {lookupResult.status === 'confirmed' && !lookupResult.checkedIn && (
              <button
                type="button"
                className="btn btn--primary btn--sm"
                style={{ marginLeft: '0.5rem' }}
                disabled={checkingId === lookupResult.id}
                onClick={() => handleCheckIn(lookupResult.id)}
              >
                {checkingId === lookupResult.id ? 'Checking in…' : 'Check in'}
              </button>
            )}
            {lookupResult.checkedIn && <span className="checkin-pill" style={{ marginLeft: '0.5rem' }}>Checked in</span>}
          </span>
        )}
      </form>

      <h2>Attendees</h2>
      {data.bookings.length === 0 ? (
        <p className="muted">No bookings yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Attendee</th>
              <th>Ticket</th>
              <th>Qty</th>
              <th>Total</th>
              <th>Reference</th>
              <th>Status</th>
              <th>Check-in</th>
              <th>Booked</th>
            </tr>
          </thead>
          <tbody>
            {data.bookings.map((b) => (
              <tr key={b.id}>
                <td>
                  {b.attendeeName}
                  <div className="muted">{b.attendeeEmail}</div>
                </td>
                <td>{b.ticketTypeName}</td>
                <td>{b.quantity}</td>
                <td>{formatMoney(b.totalAmount)}</td>
                <td>{b.reference}</td>
                <td>
                  <span className={`status-pill status-pill--${b.status}`}>{b.status}</span>
                </td>
                <td>
                  {b.status === 'confirmed' ? (
                    b.checkedIn ? (
                      <span className="checkin-pill">Checked in</span>
                    ) : (
                      <button
                        className="btn btn--ghost btn--sm"
                        disabled={checkingId === b.id}
                        onClick={() => handleCheckIn(b.id)}
                      >
                        {checkingId === b.id ? '…' : 'Check in'}
                      </button>
                    )
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td>{formatDate(b.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <OrganizerComms eventId={event.id} />
    </div>
  );
}
