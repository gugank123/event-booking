import { Link } from 'react-router-dom';
import { formatDate, formatMoney, lowestPrice, totalRemaining } from '../utils/format';

export default function EventCard({ event }) {
  const price = lowestPrice(event.ticket_types);
  const remaining = totalRemaining(event.ticket_types);
  const soldOut = remaining === 0;

  return (
    <Link to={`/events/${event.id}`} className="ticket-card">
      <div className="ticket-card__info">
        <span className="ticket-card__category">{event.category}</span>
        <h3 className="ticket-card__title">{event.title}</h3>
        <p className="ticket-card__meta">
          {formatDate(event.starts_at)} · {event.venue}, {event.city}
        </p>
      </div>
      <div className="ticket-card__perforation" aria-hidden="true">
        <span />
        <span />
      </div>
      <div className="ticket-card__stub">
        <span className="ticket-card__price">{price != null ? formatMoney(price) : '—'}</span>
        <span className="ticket-card__from">from</span>
        <span className={`ticket-card__status ${soldOut ? 'is-sold-out' : ''}`}>
          {soldOut ? 'Sold out' : `${remaining} left`}
        </span>
      </div>
    </Link>
  );
}
