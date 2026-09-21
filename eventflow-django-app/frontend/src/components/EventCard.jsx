import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { formatDate, formatMoney, lowestPrice, totalRemaining } from '../utils/format';
import { Stars } from './Stars';
import WishlistButton from './WishlistButton';

export default function EventCard({ event, index = 0 }) {
  const price = lowestPrice(event.ticket_types);
  const remaining = totalRemaining(event.ticket_types);
  const soldOut = remaining === 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: Math.min(index * 0.06, 0.5) }}
      whileHover={{ y: -6 }}
    >
      <Link to={`/events/${event.id}`} className="ticket-card">
        <div className="ticket-card__art" aria-hidden="true" />
        <WishlistButton eventId={event.id} initial={!!event.is_wishlisted} />
        {event.is_featured && <span className="featured-badge">Featured</span>}
        <div className="ticket-card__info">
          <span className="ticket-card__category">{event.category}</span>
          <h3 className="ticket-card__title">{event.title}</h3>
          <p className="ticket-card__meta">
            {formatDate(event.starts_at)} · {event.venue}, {event.city}
          </p>
          <div className="ticket-card__rating">
            <Stars value={event.avg_rating} />
            {event.review_count > 0 && <span>({event.review_count})</span>}
            {event.tickets_sold > 0 && <span>· {event.tickets_sold} going</span>}
          </div>
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
    </motion.div>
  );
}
