import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney, formatTime } from '../utils/format';

export default function EventDetail() {
  const { id } = useParams();
  const { user, token } = useAuth();
  const navigate = useNavigate();

  const [event, setEvent] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const [ticketTypeId, setTicketTypeId] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [step, setStep] = useState('browse'); // browse | checkout | confirmed
  const [card, setCard] = useState({ name: '', cardNumber: '', expiry: '', cvc: '' });
  const [checkoutError, setCheckoutError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState(null);

  useEffect(() => {
    api
      .get(`/events/${id}/`)
      .then((data) => {
        setEvent(data.event);
        if (data.event.ticket_types.length > 0) setTicketTypeId(data.event.ticket_types[0].id);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="page">Loading…</div>;
  if (error) return <div className="page">{error}</div>;
  if (!event) return <div className="page">Event not found.</div>;

  const selectedTicketType = event.ticket_types.find((t) => t.id === ticketTypeId);
  const remaining = selectedTicketType ? selectedTicketType.quantity_total - selectedTicketType.quantity_sold : 0;
  const total = selectedTicketType ? Number(selectedTicketType.price) * quantity : 0;

  function startCheckout() {
    if (!user) {
      navigate('/login', { state: { from: `/events/${id}` } });
      return;
    }
    setCheckoutError('');
    setStep('checkout');
  }

  async function handlePay(e) {
    e.preventDefault();
    setCheckoutError('');
    setSubmitting(true);
    try {
      const data = await api.post(
        '/bookings/',
        {
          eventId: event.id,
          ticketTypeId,
          quantity,
          cardNumber: card.cardNumber,
          expiry: card.expiry,
          cvc: card.cvc
        },
        token
      );
      setConfirmedBooking(data.booking);
      setStep('confirmed');
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
          <h1>You're going to {event.title}</h1>
          <p className="muted">A confirmation isn't emailed in this demo — save your reference below.</p>
          <div className="confirmation__ticket">
            <div>
              <span className="confirmation__label">Reference</span>
              <span className="confirmation__ref">{confirmedBooking.reference}</span>
            </div>
            <div>
              <span className="confirmation__label">Tickets</span>
              <span>{confirmedBooking.quantity} × {selectedTicketType.name}</span>
            </div>
            <div>
              <span className="confirmation__label">Total charged</span>
              <span>{formatMoney(confirmedBooking.totalAmount)} to card ending {confirmedBooking.cardLast4}</span>
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
      <div className="event-detail__main">
        <span className="ticket-card__category">{event.category}</span>
        <h1>{event.title}</h1>
        <p className="event-detail__meta">
          {formatDate(event.starts_at)} at {formatTime(event.starts_at)} · {event.venue}, {event.city}
        </p>
        <p className="event-detail__organizer">Hosted by {event.organizer_name}</p>
        {event.description && <p className="event-detail__description">{event.description}</p>}
      </div>

      <aside className="checkout-panel">
        {step === 'browse' && (
          <>
            <h2>Get tickets</h2>
            {event.ticket_types.length === 0 ? (
              <p className="muted">No tickets are available for this event.</p>
            ) : (
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
                          }}
                        />
                        <span className="ticket-option__name">{t.name}</span>
                        <span className="ticket-option__price">{formatMoney(t.price)}</span>
                        <span className="ticket-option__left">{left === 0 ? 'Sold out' : `${left} left`}</span>
                      </label>
                    );
                  })}
                </div>

                {selectedTicketType && remaining > 0 && (
                  <div className="quantity-row">
                    <label htmlFor="qty">Quantity</label>
                    <select id="qty" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))}>
                      {Array.from({ length: Math.min(remaining, 8) }, (_, i) => i + 1).map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="checkout-total">
                  <span>Total</span>
                  <strong>{formatMoney(total)}</strong>
                </div>

                <button className="btn btn--primary btn--block" onClick={startCheckout} disabled={!selectedTicketType || remaining === 0}>
                  {remaining === 0 ? 'Sold out' : 'Continue to checkout'}
                </button>
              </>
            )}
          </>
        )}

        {step === 'checkout' && (
          <>
            <h2>Checkout</h2>
            <p className="muted checkout-panel__note">
              This is a simulated payment — no real card is charged. Any card-shaped number works.
            </p>
            <form className="form" onSubmit={handlePay}>
              <label>
                Name on card
                <input
                  required
                  value={card.name}
                  onChange={(e) => setCard({ ...card, name: e.target.value })}
                />
              </label>
              <label>
                Card number
                <input
                  required
                  inputMode="numeric"
                  placeholder="4242 4242 4242 4242"
                  value={card.cardNumber}
                  onChange={(e) => setCard({ ...card, cardNumber: e.target.value })}
                />
              </label>
              <div className="form-row">
                <label>
                  Expiry
                  <input
                    required
                    placeholder="MM/YY"
                    value={card.expiry}
                    onChange={(e) => setCard({ ...card, expiry: e.target.value })}
                  />
                </label>
                <label>
                  CVC
                  <input
                    required
                    inputMode="numeric"
                    placeholder="123"
                    value={card.cvc}
                    onChange={(e) => setCard({ ...card, cvc: e.target.value })}
                  />
                </label>
              </div>
              <div className="checkout-total">
                <span>
                  {quantity} × {selectedTicketType.name}
                </span>
                <strong>{formatMoney(total)}</strong>
              </div>
              {checkoutError && <p className="form-error">{checkoutError}</p>}
              <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
                {submitting ? 'Processing…' : `Pay ${formatMoney(total)}`}
              </button>
              <button type="button" className="btn btn--ghost btn--block" onClick={() => setStep('browse')}>
                Back
              </button>
            </form>
          </>
        )}
      </aside>
    </div>
  );
}
