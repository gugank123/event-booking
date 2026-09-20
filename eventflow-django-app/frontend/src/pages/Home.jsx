import { useEffect, useState } from 'react';
import { api } from '../api/client';
import EventCard from '../components/EventCard';

export default function Home() {
  const [events, setEvents] = useState([]);
  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/events/categories/').then((data) => setCategories(data.categories)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    const query = params.toString();

    api
      .get(`/events/${query ? `?${query}` : ''}`)
      .then((data) => setEvents(data.events))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [search, category]);

  return (
    <div className="page">
      <section className="hero">
        <h1>Find something worth leaving the house for.</h1>
        <p>Browse concerts, conferences, and shows near you — book in a couple of clicks.</p>
        <div className="hero__search">
          <input
            type="text"
            placeholder="Search by event, venue, or city"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </section>

      {categories.length > 0 && (
        <div className="filter-row">
          <button className={`chip ${category === '' ? 'is-active' : ''}`} onClick={() => setCategory('')}>
            All
          </button>
          {categories.map((c) => (
            <button key={c} className={`chip ${category === c ? 'is-active' : ''}`} onClick={() => setCategory(c)}>
              {c}
            </button>
          ))}
        </div>
      )}

      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <p className="muted">Loading events…</p>
      ) : events.length === 0 ? (
        <p className="muted">No events match yet. Try a different search or check back soon.</p>
      ) : (
        <div className="ticket-grid">
          {events.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
