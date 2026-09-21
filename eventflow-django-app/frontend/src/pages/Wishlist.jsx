import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import EventCard from '../components/EventCard';

export default function Wishlist() {
  const { token } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get('/events/wishlist/', token)
      .then((data) => setItems(data.wishlist))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const events = items.map((item) => ({ ...item.event, is_wishlisted: true }));

  return (
    <div className="page">
      <h1>Saved for later</h1>
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <h3>Nothing saved yet.</h3>
          <p>
            Tap the heart on any event to keep it here. <Link to="/">Browse events</Link>
          </p>
        </div>
      ) : (
        <div className="ticket-grid">
          {events.map((event, i) => (
            <EventCard key={event.id} event={event} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
