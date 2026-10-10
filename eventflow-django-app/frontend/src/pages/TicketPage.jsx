import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney, formatTime } from '../utils/format';
import TicketQR from '../components/TicketQR';

/**
 * Elegant printable ticket. Data comes from the existing
 * GET /bookings/mine/ payload (tickets carry qr_token, eventTitle,
 * seatLabel, bookingReference) — no new API required.
 * "Print / Save PDF" uses the browser print dialog with a
 * print stylesheet that emits only the ticket sheet.
 */
export default function TicketPage() {
  const { ticketId } = useParams();
  const { token } = useAuth();
  const [found, setFound] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    api
      .get('/bookings/mine/', token)
      .then((data) => {
        if (cancelled) return;
        for (const b of data.bookings || []) {
          const t = (b.tickets || []).find((x) => String(x.id) === String(ticketId));
          if (t) {
            setFound({ ticket: t, booking: b });
            return;
          }
        }
        setError('Ticket not found on your account.');
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticketId, token]);

  if (loading) return <div className="page">Preparing your ticket…</div>;
  if (error || !found) {
    return (
      <div className="page page--narrow">
        <h1>Ticket</h1>
        <p className="form-error">{error || 'Ticket not found.'}</p>
        <p className="muted">
          <Link to="/my-bookings">Back to My tickets</Link>
        </p>
      </div>
    );
  }

  const { ticket, booking } = found;
  const event = booking.event || {};

  return (
    <div className="page">
      <div className="ticket-sheet">
        <div className="ticket-sheet__head">
          <p className="ticket-sheet__kicker">EventFlow · Admit one</p>
          <h2>{ticket.eventTitle || event.title || 'Event ticket'}</h2>
          <p className="ticket-sheet__venue">
            {[event.venue, event.city].filter(Boolean).join(', ')}
            {event.startsAt && ` · ${formatDate(event.startsAt)} at ${formatTime(event.startsAt)}`}
          </p>
        </div>
        <dl className="ticket-sheet__grid">
          <div>
            <dt>Ticket</dt>
            <dd className="mono">{ticket.ticket_number}</dd>
          </div>
          <div>
            <dt>Booking reference</dt>
            <dd className="mono">{ticket.bookingReference || booking.reference}</dd>
          </div>
          <div>
            <dt>Seat</dt>
            <dd>{ticket.seatLabel || `${booking.quantity} × ${booking.ticketTypeName}`}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{ticket.status}</dd>
          </div>
        </dl>
        <div className="ticket-sheet__stub">
          <TicketQR value={ticket.qr_token} label={ticket.ticket_number} size={160} />
          <p className="ticket-sheet__note">
            Present this code at the door. Each ticket admits once — screenshots are welcome, duplicates are
            not. Paid {formatMoney(booking.totalAmount)} · {ticket.eventTitle || event.title || ''}.
          </p>
        </div>
      </div>
      <div className="ticket-actions">
        <button className="btn btn--primary" onClick={() => window.print()}>
          Print / Save as PDF
        </button>
        <Link className="btn btn--ghost" to="/my-bookings">
          Back to My tickets
        </Link>
      </div>
    </div>
  );
}
