import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney } from '../utils/format';
import TicketQR from '../components/TicketQR';
import ContactOrganizer from '../components/ContactOrganizer';

function loadRazorpay() {
  if (window.Razorpay) return Promise.resolve(true);
  return new Promise((resolve) => {
    const s = document.createElement('script');
    s.src = 'https://checkout.razorpay.com/v1/checkout.js';
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

export default function MyBookings() {
  const { token, user } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [tab, setTab] = useState('all');

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
    if (!window.confirm('Cancel this booking? Seats are released and paid bookings start a gateway refund.')) return;
    setBusyId(id);
    try {
      const res = await api.post(`/bookings/${id}/cancel/`, {}, token);
      if (res.refund) {
        alert(`Refund ${res.refund.status}: ₹${res.refund.amount}. Track it below.`);
      }
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handlePayPending(booking) {
    setBusyId(booking.id);
    setError('');
    try {
      const order = await api.post('/payments/create-order/', { booking_id: booking.id }, token);
      const verify = async (paymentId, signature) => {
        await api.post(
          '/payments/verify/',
          { order_id: order.order_id, payment_id: paymentId, signature },
          token
        );
        load();
      };
      if (order.order_id.startsWith('order_TEST_')) {
        await verify('pay_TEST_local', 'test');
        return;
      }
      const ok = await loadRazorpay();
      if (!ok) throw new Error('Could not load the payment gateway.');
      await new Promise((resolve, reject) => {
        const rzp = new window.Razorpay({
          key: order.key_id,
          amount: Math.round(Number(order.amount) * 100),
          currency: order.currency || 'INR',
          name: 'EventFlow',
          description: booking.event?.title || 'Tickets',
          order_id: order.order_id,
          prefill: { email: user.email, name: user.name },
          theme: { color: '#6c3df5' },
          handler: (resp) => verify(resp.razorpay_payment_id, resp.razorpay_signature).then(resolve).catch(reject),
          modal: { ondismiss: () => reject(new Error('Payment window closed.')) }
        });
        rzp.on('payment.failed', (r) => reject(new Error(r?.error?.description || 'Payment failed.')));
        rzp.open();
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  const visible = bookings.filter((b) => {
    if (tab === 'upcoming') return b.status === 'confirmed' && new Date(b.event?.startsAt) >= new Date();
    if (tab === 'past') return !(b.status === 'confirmed' && new Date(b.event?.startsAt) >= new Date());
    return true;
  });

  return (
    <div className="page">
      <div className="page-header">
        <h1>My tickets</h1>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {['all', 'upcoming', 'past'].map((t) => (
            <button
              key={t}
              className={`btn btn--sm ${tab === t ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setTab(t)}
            >
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
          <Link className="btn btn--ghost btn--sm" to="/invitations">Invitations</Link>
          <Link className="btn btn--ghost btn--sm" to="/messages">Messages</Link>
          <Link className="btn btn--ghost btn--sm" to="/support">Support</Link>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="empty-state">
          <h3>No bookings here.</h3>
          <p>
            <Link to="/">Browse events</Link> to get started.
          </p>
        </div>
      ) : (
        <div className="booking-list">
          {visible.map((b, i) => (
            <motion.div
              key={b.id}
              className={`booking-row ${['cancelled', 'refunded', 'expired'].includes(b.status) ? 'is-cancelled' : ''}`}
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
                {b.seats?.length > 0 && <p className="muted">Seats: {b.seats.join(', ')}</p>}
                {b.coupon_code && <p className="muted">Coupon {b.coupon_code} (−{formatMoney(b.discount)})</p>}
              </div>
              <div className="booking-row__details">
                <span>{b.quantity} × {b.ticketTypeName}</span>
                <span>{formatMoney(b.totalAmount)}</span>
                <span className={`status-pill status-pill--${b.status}`}>{b.status.replace('_', ' ')}</span>
                {b.checkedIn && <span className="checkin-pill">Checked in</span>}
              </div>
              <div className="booking-row__qr">
                {b.event && (
                  <ContactOrganizer eventId={b.event.id} bookingId={b.id} eventTitle={b.event.title} />
                )}
                {b.status === 'pending_payment' && (
                  <button
                    className="btn btn--primary btn--sm"
                    disabled={busyId === b.id}
                    onClick={() => handlePayPending(b)}
                    style={{ marginLeft: '0.5rem' }}
                  >
                    {busyId === b.id ? 'Processing…' : 'Pay now'}
                  </button>
                )}
                {(b.status === 'confirmed' || b.status === 'pending_payment') && (
                  <button
                    className="btn btn--ghost btn--sm"
                    disabled={busyId === b.id}
                    onClick={() => handleCancel(b.id)}
                    style={{ marginLeft: '0.5rem' }}
                  >
                    {busyId === b.id ? 'Cancelling…' : 'Cancel'}
                  </button>
                )}
                {b.status === 'confirmed' && (
                  <button
                    className="btn btn--ghost btn--sm"
                    style={{ marginLeft: '0.5rem' }}
                    onClick={() => setExpanded(expanded === b.id ? null : b.id)}
                  >
                    {expanded === b.id ? 'Hide tickets' : 'Tickets'}
                  </button>
                )}
              </div>
              {expanded === b.id && b.status === 'confirmed' && (
                <div style={{ gridColumn: '1 / -1' }}>
                  <p className="muted" style={{ textAlign: 'center' }}>
                    Show a QR at the door — each ticket scans exactly once{b.checkedIn ? ' (already checked in).' : '.'}
                  </p>
                  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                    {(b.tickets || []).map((t) => (
                      <div key={t.id} style={{ textAlign: 'center' }}>
                        <TicketQR value={t.qr_token} label={t.ticket_number} />
                        <p className="muted">{t.seatLabel || `${b.quantity} × ${b.ticketTypeName}`} · {t.status}</p>
                        <Link className="btn btn--ghost btn--sm" to={`/tickets/${t.id}`}>
                          Ticket / Print
                        </Link>
                      </div>
                    ))}
                    {(b.tickets || []).length === 0 && (
                      <p className="muted">Tickets are being generated — pull to refresh.</p>
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
