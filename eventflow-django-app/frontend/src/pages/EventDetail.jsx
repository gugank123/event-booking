import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api, imageSrc } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney, formatTime } from '../utils/format';
import { Stars } from '../components/Stars';
import Reviews from '../components/Reviews';
import WishlistButton from '../components/WishlistButton';
import ContactOrganizer from '../components/ContactOrganizer';

function loadRazorpay() {
  if (window.Razorpay) return Promise.resolve(true);
  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

function fmtCountdown(s) {
  const m = Math.floor(Math.max(0, s) / 60);
  const r = Math.max(0, s) % 60;
  return `${m}:${String(r).padStart(2, '0')}`;
}

export default function EventDetail({ preview = false }) {
  const { id } = useParams();
  const { user, token } = useAuth();
  const navigate = useNavigate();

  const [event, setEvent] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const [ticketTypeId, setTicketTypeId] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [coupon, setCoupon] = useState('');
  const [step, setStep] = useState('browse'); // browse | pay | confirmed
  const [heldBooking, setHeldBooking] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [checkoutError, setCheckoutError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState(null);
  const [announcements, setAnnouncements] = useState([]);

  useEffect(() => {
    // Pass the token when signed in so the response includes is_wishlisted.
    api
      .get(`/events/${id}/`, token)
      .then((data) => {
        setEvent(data.event);
        if (data.event.ticket_types.length > 0) setTicketTypeId(data.event.ticket_types[0].id);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, token]);

  useEffect(() => {
    api
      .get(`/comms/announcements/event/${id}/`)
      .then((data) => setAnnouncements(data.announcements))
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    if (step !== 'pay' || secondsLeft <= 0) return;
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [step, secondsLeft]);

  useEffect(() => {
    if (step === 'pay' && secondsLeft <= 0 && heldBooking) {
      setCheckoutError('Your seat hold expired. Please start again.');
      setStep('browse');
      setHeldBooking(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsLeft]);

  if (loading) return <div className="page">Loading…</div>;
  if (error) return <div className="page">{error}</div>;
  if (!event) return <div className="page">Event not found.</div>;

  const selectedTicketType = event.ticket_types.find((t) => t.id === ticketTypeId);
  const remaining = selectedTicketType ? selectedTicketType.quantity_total - selectedTicketType.quantity_sold : 0;
  const maxPerUser = selectedTicketType ? selectedTicketType.max_per_user || 8 : 8;
  const qtyCap = Math.min(remaining, maxPerUser, 8);
  const isReserved = event.seating_type === 'reserved';
  const seatTotal = selectedSeats.reduce((sum, s) => sum + Number(s.price), 0);
  const total = isReserved ? seatTotal : selectedTicketType ? Number(selectedTicketType.price) * quantity : 0;
  const now = new Date();
  const bookingNotOpen = event.booking_opens_at && new Date(event.booking_opens_at) > now;
  const bookingClosed = event.booking_closes_at && new Date(event.booking_closes_at) < now;
  const bookingBlocked = bookingNotOpen || bookingClosed;

  const seatsBySection = {};
  if (isReserved && event.seats) {
    for (const s of event.seats) {
      (seatsBySection[s.section] = seatsBySection[s.section] || []).push(s);
    }
    for (const k of Object.keys(seatsBySection)) {
      seatsBySection[k].sort((a, b) => (a.row_label < b.row_label ? -1 : a.row_label > b.row_label ? 1 : a.number - b.number));
    }
  }

  function toggleSeat(seat) {
    if (seat.status !== 'available') return;
    setSelectedSeats((prev) => {
      if (prev.some((s) => s.id === seat.id)) return prev.filter((s) => s.id !== seat.id);
      if (prev.length >= 10) return prev;
      return [...prev, seat];
    });
  }

  async function startCheckout() {
    if (!user) {
      navigate('/login', { state: { from: `/events/${id}` } });
      return;
    }
    setCheckoutError('');
    setSubmitting(true);
    try {
      // Server computes all prices + validates coupon; seats are HELD for ~8 min.
      const data = await api.post(
        '/bookings/',
        {
          eventId: event.id,
          ticketTypeId,
          quantity: isReserved ? selectedSeats.length : quantity,
          seat_ids: isReserved ? selectedSeats.map((s) => s.id) : [],
          coupon_code: coupon.trim().toUpperCase()
        },
        token
      );
      setHeldBooking(data.booking);
      setSecondsLeft(data.expires_in_seconds || 480);
      setStep('pay');
    } catch (err) {
      setCheckoutError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePay() {
    setCheckoutError('');
    setSubmitting(true);
    try {
      const order = await api.post('/payments/create-order/', { booking_id: heldBooking.id }, token);
      const verify = async (paymentId, signature) => {
        const res = await api.post(
          '/payments/verify/',
          { order_id: order.order_id, payment_id: paymentId, signature },
          token
        );
        const detail = await api.get(`/bookings/${res.booking_id}/`, token);
        setConfirmedBooking(detail.booking);
        setStep('confirmed');
      };
      if (order.order_id.startsWith('order_TEST_')) {
        // No gateway keys configured (local dev): complete via the test path.
        await verify('pay_TEST_local', 'test');
        return;
      }
      const ok = await loadRazorpay();
      if (!ok) throw new Error('Could not load the payment gateway. Check your connection and retry.');
      await new Promise((resolve, reject) => {
        const rzp = new window.Razorpay({
          key: order.key_id,
          amount: Math.round(Number(order.amount) * 100),
          currency: order.currency || 'INR',
          name: 'EventFlow',
          description: event.title,
          order_id: order.order_id,
          prefill: { email: user.email, name: user.name },
          theme: { color: '#6c3df5' },
          handler: async (resp) => {
            try {
              await verify(resp.razorpay_payment_id, resp.razorpay_signature);
              resolve();
            } catch (e) {
              reject(e);
            }
          },
          modal: { ondismiss: () => reject(new Error('Payment window closed before completion.')) }
        });
        rzp.on('payment.failed', (resp) => reject(new Error(resp?.error?.description || 'Payment failed.')));
        rzp.open();
      });
    } catch (err) {
      setCheckoutError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (step === 'confirmed' && confirmedBooking) {
    return (
      <div className="page page--narrow">
        <div className="confirmation">
          <span className="confirmation__badge">Booking confirmed</span>
          <h1>You&apos;re going to {event.title}</h1>
          <p className="muted">Payment verified — a confirmation email with your tickets was sent.</p>
          <div className="confirmation__ticket">
            <div>
              <span className="confirmation__label">Reference</span>
              <span className="confirmation__ref">{confirmedBooking.reference}</span>
            </div>
            <div>
              <span className="confirmation__label">Tickets</span>
              <span>{confirmedBooking.quantity} × {confirmedBooking.ticketTypeName}</span>
            </div>
            {confirmedBooking.seats?.length > 0 && (
              <div>
                <span className="confirmation__label">Seats</span>
                <span>{confirmedBooking.seats.join(', ')}</span>
              </div>
            )}
            <div>
              <span className="confirmation__label">Total paid</span>
              <span>{formatMoney(confirmedBooking.totalAmount)} (incl. fees)</span>
            </div>
          </div>
          <button className="btn btn--primary" onClick={() => navigate('/my-bookings')}>
            View my tickets
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page event-detail">
      <div>
        {preview && (
          <div className="preview-banner">
            <span>👁 Preview — this is exactly how attendees see this event{event.status !== 'published' ? ` (currently ${event.status})` : ''}.</span>
            <Link className="btn btn--primary btn--sm" to={`/organizer/events/${event.id}/edit`}>
              Back to editing
            </Link>
          </div>
        )}
        <motion.div
          className="event-detail__main"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          {imageSrc(event.display_image || event.image_url) && (
            <img className="event-poster" src={imageSrc(event.display_image || event.image_url)} alt={event.title} />
          )}
          <span className="ticket-card__category">{event.category}</span>
          {event.is_featured && <span className="featured-badge">Featured</span>}
          <span className={`status-pill status-pill--${event.status === 'published' ? 'published' : event.status === 'draft' ? 'draft' : 'cancelled'}`} style={{ marginLeft: '0.5rem' }}>
            {event.status}
          </span>
          <h1>{event.title}</h1>
          {event.short_description && <p className="event-detail__tagline">{event.short_description}</p>}
          <p className="event-detail__meta">
            {formatDate(event.starts_at)} at {formatTime(event.starts_at)} · {event.venue}, {event.city}
          </p>
          <p className="event-detail__organizer">
            Hosted by {event.organizer_name}
            {event.organizer_contact && <> · {event.organizer_contact}</>}
          </p>
          {(event.address || event.state || event.pincode) && (
            <p className="muted">
              {[event.address, event.city, event.state, event.pincode].filter(Boolean).join(', ')}
              {event.map_link && (
                <>
                  {' '}· <a href={event.map_link} target="_blank" rel="noreferrer">View map</a>
                </>
              )}
            </p>
          )}
          {event.booking_closes_at && (
            <p className="muted">Booking closes {formatDate(event.booking_closes_at)} at {formatTime(event.booking_closes_at)}</p>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: '0.5rem 0', flexWrap: 'wrap' }}>
            <Stars value={event.avg_rating} />
            {event.review_count > 0 && <span className="muted">({event.review_count} reviews)</span>}
            {event.tickets_sold > 0 && <span className="muted">· {event.tickets_sold} tickets sold</span>}
            {!preview && <WishlistButton eventId={event.id} initial={!!event.is_wishlisted} inline />}
          </div>
          {event.description && <p className="event-detail__description">{event.description}</p>}
          {!preview && (
            <div style={{ marginTop: '1rem' }}>
              <ContactOrganizer eventId={event.id} eventTitle={event.title} />
            </div>
          )}
        </motion.div>
        {announcements.length > 0 && (
          <section className="announcements">
            <h2>Announcements from the organizer</h2>
            {announcements.map((a) => (
              <div key={a.id} className="review">
                <div className="review__head">
                  <span className="review__author">{a.title}</span>
                  <span className="review__date">{formatDate(a.created_at)}</span>
                </div>
                <p>{a.message}</p>
              </div>
            ))}
          </section>
        )}
        <Reviews eventId={event.id} />
      </div>

      <aside className="checkout-panel">
        {preview ? (
          <>
            <h2>Get tickets</h2>
            <p className="muted">This is a preview — booking is disabled here. Publish the event for live sales.</p>
            <button className="btn btn--primary btn--block" disabled>
              Book now
            </button>
          </>
        ) : step === 'browse' && (
          <>
            <h2>Get tickets</h2>
            {bookingNotOpen && (
              <p className="form-ok">Booking opens {formatDate(event.booking_opens_at)} at {formatTime(event.booking_opens_at)}.</p>
            )}
            {bookingClosed && <p className="form-error">Booking for this event has closed.</p>}
            {!bookingBlocked && event.ticket_types.length === 0 ? (
              <p className="muted">No tickets are available for this event.</p>
            ) : !bookingBlocked && (
              <>
                <div className="ticket-options">
                  {event.ticket_types.map((t) => {
                    const left = t.quantity_total - t.quantity_sold;
                    return (
                      <label key={t.id} className={`ticket-option ${ticketTypeId === t.id ? 'is-selected' : ''} ${left === 0 ? 'is-disabled' : ''}`}>
                        <input
                          type="radio"
                          name="ticketType"
                          disabled={left === 0}
                          checked={ticketTypeId === t.id}
                          onChange={() => {
                            setTicketTypeId(t.id);
                            setQuantity(1);
                            setSelectedSeats([]);
                          }}
                        />
                        <span className="ticket-option__name">{t.name}</span>
                        <span className="ticket-option__price">{formatMoney(t.price)}</span>
                        <span className="ticket-option__left">
                          {left === 0 ? 'Sold out' : `${left} left · max ${t.max_per_user || 8}/person`}
                        </span>
                      </label>
                    );
                  })}
                </div>

                {isReserved ? (
                  <div className="seat-map">
                    <p className="muted">Pick your seats ({selectedSeats.length}/10):</p>
                    {Object.keys(seatsBySection).length === 0 && (
                      <p className="muted">Seat map coming soon — check back shortly.</p>
                    )}
                    {Object.entries(seatsBySection).map(([section, seats]) => (
                      <div key={section} className="seat-section">
                        <strong>{section}</strong>
                        <div className="seat-grid">
                          {seats.map((s) => {
                            const active = selectedSeats.some((x) => x.id === s.id);
                            return (
                              <button
                                key={s.id}
                                type="button"
                                disabled={s.status !== 'available'}
                                title={`${s.section} ${s.row_label}${s.number} — ${formatMoney(s.price)}${s.status === 'held' ? ' (held)' : ''}`}
                                className={`seat ${s.status !== 'available' ? 'is-taken' : ''} ${active ? 'is-selected' : ''}`}
                                onClick={() => toggleSeat(s)}
                              >
                                {s.row_label}{s.number}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                    {selectedSeats.length > 0 && (
                      <p className="muted">Selected: {selectedSeats.map((s) => `${s.section} ${s.row_label}${s.number}`).join(', ')}</p>
                    )}
                  </div>
                ) : (
                  selectedTicketType && remaining > 0 && (
                    <div className="quantity-row">
                      <label htmlFor="qty">Quantity</label>
                      <select id="qty" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))}>
                        {Array.from({ length: Math.max(qtyCap, 1) }, (_, i) => i + 1).map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </div>
                  )
                )}

                <label style={{ display: 'block', marginTop: '0.5rem' }}>
                  Coupon (optional)
                  <input
                    placeholder="SAVE10"
                    value={coupon}
                    onChange={(e) => setCoupon(e.target.value.toUpperCase())}
                  />
                </label>

                <div className="checkout-total">
                  <span>Total</span>
                  <strong>{formatMoney(total)}</strong>
                </div>
                <p className="muted">Final price (discounts + fees) is calculated securely at checkout.</p>

                {checkoutError && <p className="form-error">{checkoutError}</p>}
                <button
                  className="btn btn--primary btn--block"
                  onClick={startCheckout}
                  disabled={submitting || !selectedTicketType || remaining === 0 || (isReserved && selectedSeats.length === 0)}
                >
                  {submitting ? 'Holding seats…' : remaining === 0 ? 'Sold out' : 'Continue to payment'}
                </button>
              </>
            )}
          </>
        )}

        {step === 'pay' && heldBooking && (
          <>
            <h2>Complete payment</h2>
            <p className="form-ok">Seats held for {fmtCountdown(secondsLeft)} — complete payment before the timer ends.</p>
            <div className="confirmation__ticket">
              <div>
                <span className="confirmation__label">Reference</span>
                <span className="confirmation__ref">{heldBooking.reference}</span>
              </div>
              <div>
                <span className="confirmation__label">Subtotal</span>
                <span>{formatMoney(heldBooking.subtotal)}</span>
              </div>
              {Number(heldBooking.discount) > 0 && (
                <div>
                  <span className="confirmation__label">Coupon {heldBooking.coupon_code}</span>
                  <span>−{formatMoney(heldBooking.discount)}</span>
                </div>
              )}
              <div>
                <span className="confirmation__label">Fees &amp; tax</span>
                <span>{formatMoney(Number(heldBooking.platformFee || 0))}</span>
              </div>
              <div>
                <span className="confirmation__label">Total due</span>
                <span>{formatMoney(heldBooking.totalAmount)}</span>
              </div>
            </div>
            <p className="muted checkout-panel__note">
              Secured by Razorpay (UPI, cards, netbanking). We never see or store your payment details.
            </p>
            {checkoutError && <p className="form-error">{checkoutError}</p>}
            <button className="btn btn--primary btn--block" onClick={handlePay} disabled={submitting}>
              {submitting ? 'Processing…' : `Pay ${formatMoney(heldBooking.totalAmount)}`}
            </button>
            <button type="button" className="btn btn--ghost btn--block" onClick={() => { setStep('browse'); setHeldBooking(null); }}>
              Back
            </button>
          </>
        )}
      </aside>
    </div>
  );
}
