import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { api } from '../api/client';
import EventCard from '../components/EventCard';
import { Stars } from '../components/Stars';
import { formatDate, formatMoney, lowestPrice } from '../utils/format';

const ORDERINGS = [
  { value: 'starts_at', label: 'Date: soonest' },
  { value: '-starts_at', label: 'Date: latest' },
  { value: 'popular', label: 'Most popular' },
  { value: 'rating', label: 'Top rated' },
  { value: 'price_low', label: 'Price: low to high' },
  { value: 'price_high', label: 'Price: high to low' }
];

export default function Home() {
  const [events, setEvents] = useState([]);
  const [categories, setCategories] = useState([]);
  const [spotlight, setSpotlight] = useState(null);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [ordering, setOrdering] = useState('starts_at');
  const [featuredOnly, setFeaturedOnly] = useState(false);
  const [trendingOnly, setTrendingOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.get('/events/categories/').then((data) => setCategories(data.categories)).catch(() => {});
    api
      .get('/events/?featured=true&page_size=1')
      .then((data) => setSpotlight(data.events[0] || null))
      .catch(() => {});
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setFailed(false);
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    if (ordering) params.set('ordering', ordering);
    if (featuredOnly) params.set('featured', 'true');
    if (trendingOnly) params.set('trending', 'true');
    params.set('page', String(page));

    api
      .get(`/events/?${params.toString()}`)
      .then((data) => {
        setEvents(data.events);
        setPages(data.pages);
        setTotal(data.total);
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [search, category, dateFrom, dateTo, ordering, featuredOnly, trendingOnly, page]);

  useEffect(() => {
    setPage(1);
  }, [search, category, dateFrom, dateTo, ordering, featuredOnly, trendingOnly]);

  useEffect(load, [load]);

  function clearFilters() {
    setSearch('');
    setCategory('');
    setDateFrom('');
    setDateTo('');
    setOrdering('starts_at');
    setFeaturedOnly(false);
    setTrendingOnly(false);
    setPage(1);
  }

  const filtering = search || category || dateFrom || dateTo || featuredOnly || trendingOnly;

  return (
    <div className="page">
      <section className="hero">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55 }}
        >
          Nights you'll <em>never forget</em> start here.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.1 }}
        >
          Hand-picked concerts, conferences and shows — rated by real attendees, scanned at the door, backed by
          organisers you can actually reach.
        </motion.p>
        <motion.div
          className="hero__search"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.2 }}
        >
          <input
            type="text"
            placeholder="Search by event, venue, or city"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </motion.div>
        <motion.div
          className="hero__cta"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.25 }}
        >
          <a className="btn btn--primary" href="#browse">
            🎟 Book an event
          </a>
          <Link className="btn btn--ghost" to="/post-event">
            ＋ Post an event
          </Link>
        </motion.div>
        <motion.div
          className="hero__stats"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.55, delay: 0.3 }}
        >          <div className="hero__stat">
            <strong>{total}</strong>
            <span>Live events</span>
          </div>
          <div className="hero__stat">
            <strong>{categories.length}</strong>
            <span>Categories</span>
          </div>
          <div className="hero__stat">
            <strong>QR</strong>
            <span>Door entry</span>
          </div>
        </motion.div>
      </section>

      {spotlight && !filtering && (
        <>
          <div className="section-head">
            <h2>In the spotlight</h2>
            <span className="muted">Hand-picked by our editors</span>
          </div>
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <Link to={`/events/${spotlight.id}`} className="spotlight">
              <div className="spotlight__art" aria-hidden="true" />
              <div className="spotlight__body">
                <span className="ticket-card__category">{spotlight.category}</span>
                <h3>{spotlight.title}</h3>
                <p className="muted">
                  {formatDate(spotlight.starts_at)} · {spotlight.venue}, {spotlight.city}
                </p>
                <Stars value={spotlight.avg_rating} />
                <span className="btn btn--primary">
                  {lowestPrice(spotlight.ticket_types) != null
                    ? `Get tickets from ${formatMoney(lowestPrice(spotlight.ticket_types))}`
                    : 'View event'}
                </span>
              </div>
            </Link>
          </motion.div>
        </>
      )}

      <div className="section-head" id="browse">
        <h2>Browse everything</h2>
        {total > 0 && <span className="muted">{total} event{total === 1 ? '' : 's'}</span>}
      </div>

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

      <div className="discovery-bar">
        <label>
          Sort
          <select value={ordering} onChange={(e) => setOrdering(e.target.value)}>
            {ORDERINGS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          From
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        <button
          type="button"
          className={`toggle-pill ${featuredOnly ? 'is-on' : ''}`}
          onClick={() => setFeaturedOnly((v) => !v)}
        >
          ★ Featured
        </button>
        <button
          type="button"
          className={`toggle-pill ${trendingOnly ? 'is-on' : ''}`}
          onClick={() => setTrendingOnly((v) => !v)}
        >
          ▲ Trending
        </button>
      </div>

      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      ) : failed || events.length === 0 ? (
        <div className="empty-state">
          <h3>{failed ? 'Nothing to show right now.' : 'No events match those filters.'}</h3>
          <p>
            {failed
              ? 'Check your connection and give it another go.'
              : 'Try widening the dates or clearing a filter or two.'}
          </p>
          <button
            className="btn btn--primary"
            onClick={failed ? load : clearFilters}
            style={{ marginTop: '1rem' }}
          >
            {failed ? 'Try again' : 'Show everything'}
          </button>
        </div>
      ) : (
        <>
          <div className="ticket-grid">
            <AnimatePresence mode="popLayout">
              {events.map((event, i) => (
                <EventCard key={event.id} event={event} index={i} />
              ))}
            </AnimatePresence>
          </div>
          {pages > 1 && (
            <div className="pagination">
              <button className="page-btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                ‹
              </button>
              {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  className={`page-btn ${n === page ? 'is-current' : ''}`}
                  onClick={() => setPage(n)}
                >
                  {n}
                </button>
              ))}
              <button className="page-btn" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
                ›
              </button>
              <span className="pagination__info">
                Page {page} of {pages}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
