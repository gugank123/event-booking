import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney } from '../utils/format';

export default function OrganizerEventBookings() {
  const { id } = useParams();
  const { token } = useAuth();
  const [event, setEvent] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get(`/events/${id}/`), api.get(`/events/${id}/bookings/`, token)])
      .then(([eventData, bookingData]) => {
        setEvent(eventData.event);
        setData(bookingData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, token]);

  if (loading) return <div className="page">Loading…</div>;
  if (error) return <div className="page">{error}</div>;

  return (
    <div className="page">
      <h1>{event.title}</h1>
      <div className="stat-row">
        <div className="stat-card">
          <span className="stat-card__value">{formatMoney(data.revenue)}</span>
          <span className="stat-card__label">Revenue</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__value">{data.ticketsSold}</span>
          <span className="stat-card__label">Tickets sold</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__value">{data.bookings.length}</span>
          <span className="stat-card__label">Total orders</span>
        </div>
      </div>

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
                <td>{formatDate(b.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
