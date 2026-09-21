import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney } from '../utils/format';
import { Stars } from '../components/Stars';

const FALLBACK_CATEGORIES = ['Music', 'Conference', 'Comedy', 'Sports', 'Theatre', 'Food & Drink', 'Outdoors', 'Workshop', 'Other'];

function emptyTicketType() {
  return { key: crypto.randomUUID(), name: '', price: '', quantity_total: '' };
}

function toISO(local) {
  return local ? new Date(local).toISOString() : null;
}

export default function OrganizerEventForm() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';

  const [categories, setCategories] = useState(FALLBACK_CATEGORIES);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Music');
  const [customCategory, setCustomCategory] = useState('');
  const [venue, setVenue] = useState('');
  const [city, setCity] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [description, setDescription] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [status, setStatus] = useState('published');
  const [isFeatured, setIsFeatured] = useState(false);
  const [ticketTypes, setTicketTypes] = useState([emptyTicketType()]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .get('/events/categories/')
      .then((data) => {
        const merged = [...new Set([...FALLBACK_CATEGORIES, ...(data.categories || [])])];
        setCategories(merged);
      })
      .catch(() => {});
  }, []);

  function updateTicketType(key, field, value) {
    setTicketTypes((rows) => rows.map((r) => (r.key === key ? { ...r, [field]: value } : r)));
  }

  function addTicketType() {
    setTicketTypes((rows) => [...rows, emptyTicketType()]);
  }

  function removeTicketType(key) {
    setTicketTypes((rows) => (rows.length > 1 ? rows.filter((r) => r.key !== key) : rows));
  }

  const summary = useMemo(() => {
    let capacity = 0;
    let revenue = 0;
    for (const t of ticketTypes) {
      const qty = Number(t.quantity_total) || 0;
      const price = Number(t.price) || 0;
      capacity += qty;
      revenue += qty * price;
    }
    return { capacity, revenue, tiers: ticketTypes.length };
  }, [ticketTypes]);

  const dateProblem =
    startsAt && endsAt && new Date(endsAt) <= new Date(startsAt)
      ? 'End time must be after start time.'
      : startsAt && new Date(startsAt) < new Date()
        ? 'Start time is in the past — the event would be over before it begins.'
        : '';

  const effectiveCategory = category === '__custom' ? customCategory.trim() : category;

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (dateProblem) {
      setError(dateProblem);
      return;
    }
    if (!effectiveCategory) {
      setError('Pick a category or type your own.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        title: title.trim(),
        category: effectiveCategory,
        venue: venue.trim(),
        city: city.trim(),
        starts_at: toISO(startsAt),
        ends_at: toISO(endsAt) || toISO(startsAt),
        description: description.trim(),
        image_url: imageUrl.trim(),
        status,
        is_featured: isAdmin ? isFeatured : false,
        ticket_types: ticketTypes.map((t) => ({
          name: t.name.trim(),
          price: Number(t.price),
          quantity_total: Number(t.quantity_total)
        }))
      };
      const data = await api.post('/events/', payload, token);
      navigate(`/organizer/events/${data.event.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const previewImage = imageUrl.trim();
  const previewMin = ticketTypes.some((t) => String(t.price).trim() !== '')
    ? formatMoney(Math.min(...ticketTypes.map((t) => Number(t.price) || 0)))
    : '—';

  return (
    <div className="page">
      <h1>Create an event post</h1>
      <p className="muted">Fill in every detail below — the live preview on the right shows what attendees will see.</p>

      <div className="create-layout">
        <motion.form
          className="form"
          onSubmit={handleSubmit}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h3 className="form-section-title">1 · The basics</h3>
          <label>
            Event title
            <input required value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} placeholder="e.g. Neon Pulse: Synthwave Night" />
          </label>
          <div className="form-row">
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
                <option value="__custom">＋ New category…</option>
              </select>
            </label>
            {category === '__custom' && (
              <label>
                Your category
                <input value={customCategory} onChange={(e) => setCustomCategory(e.target.value)} maxLength={60} placeholder="e.g. Poetry" />
              </label>
            )}
          </div>
          <label>
            Description
            <textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What happens, who it's for, what to expect…" />
          </label>
          <label>
            Cover image URL <span className="muted">(optional)</span>
            <input type="url" value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="https://…" />
          </label>

          <h3 className="form-section-title">2 · When & where</h3>
          <div className="form-row">
            <label>
              Venue
              <input required value={venue} onChange={(e) => setVenue(e.target.value)} maxLength={200} placeholder="e.g. Riverside Park" />
            </label>
            <label>
              City
              <input required value={city} onChange={(e) => setCity(e.target.value)} maxLength={120} placeholder="e.g. Austin" />
            </label>
          </div>
          <div className="form-row">
            <label>
              Starts at
              <input required type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} />
            </label>
            <label>
              Ends at <span className="muted">(optional)</span>
              <input type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} />
            </label>
          </div>
          {dateProblem && <p className="form-error">{dateProblem}</p>}

          <h3 className="form-section-title">3 · Tickets</h3>
          <fieldset className="ticket-type-builder">
            <legend>Ticket types (at least one)</legend>
            {ticketTypes.map((t) => (
              <div className="ticket-type-row" key={t.key}>
                <input
                  placeholder="Name (e.g. General admission)"
                  required
                  value={t.name}
                  onChange={(e) => updateTicketType(t.key, 'name', e.target.value)}
                />
                <input
                  placeholder="Price"
                  type="number"
                  min="0"
                  step="0.01"
                  required
                  value={t.price}
                  onChange={(e) => updateTicketType(t.key, 'price', e.target.value)}
                />
                <input
                  placeholder="Quantity"
                  type="number"
                  min="1"
                  required
                  value={t.quantity_total}
                  onChange={(e) => updateTicketType(t.key, 'quantity_total', e.target.value)}
                />
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => removeTicketType(t.key)}
                  aria-label="Remove ticket type"
                >
                  ✕
                </button>
              </div>
            ))}
            <button type="button" className="btn btn--ghost btn--sm" onClick={addTicketType}>
              + Add another ticket type
            </button>
            <p className="muted">
              {summary.tiers} tier{summary.tiers === 1 ? '' : 's'} · {summary.capacity} total seats ·
              up to {formatMoney(summary.revenue)} revenue
            </p>
          </fieldset>

          <h3 className="form-section-title">4 · Publishing</h3>
          <fieldset className="role-choice">
            <legend>Visibility</legend>
            <label className={`role-option ${status === 'published' ? 'is-selected' : ''}`}>
              <input type="radio" name="status" value="published" checked={status === 'published'} onChange={() => setStatus('published')} />
              Publish immediately — attendees can find and book it
            </label>
            <label className={`role-option ${status === 'draft' ? 'is-selected' : ''}`}>
              <input type="radio" name="status" value="draft" checked={status === 'draft'} onChange={() => setStatus('draft')} />
              Save as draft — hidden until you publish it later
            </label>
          </fieldset>
          {isAdmin && (
            <label className="check-row">
              <input type="checkbox" checked={isFeatured} onChange={(e) => setIsFeatured(e.target.checked)} />
              Feature on the homepage spotlight
            </label>
          )}

          {error && <p className="form-error">{error}</p>}
          <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
            {submitting ? 'Posting…' : status === 'draft' ? 'Save draft' : 'Publish event post'}
          </button>
        </motion.form>

        <aside className="preview-pane">
          <h3 className="form-section-title">Live preview</h3>
          <div className="ticket-card ticket-card--preview">
            {previewImage ? (
              <img className="preview-img" src={previewImage} alt="" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
            ) : (
              <div className="ticket-card__art" aria-hidden="true" />
            )}
            <div className="ticket-card__info">
              <span className="ticket-card__category">{effectiveCategory || 'Category'}</span>
              <h3 className="ticket-card__title">{title || 'Your event title'}</h3>
              <p className="ticket-card__meta">
                {startsAt ? formatDate(startsAt) : 'Pick a date'} · {venue || 'Venue'}, {city || 'City'}
              </p>
              <div className="ticket-card__rating">
                <Stars value={null} />
              </div>
            </div>
            <div className="ticket-card__perforation" aria-hidden="true">
              <span />
              <span />
            </div>
            <div className="ticket-card__stub">
              <span className="ticket-card__price">{previewMin}</span>
              <span className="ticket-card__from">from</span>
              <span className="ticket-card__status">{summary.capacity} seats</span>
            </div>
          </div>
          {description && <p className="muted preview-desc">{description.slice(0, 220)}{description.length > 220 ? '…' : ''}</p>}
          <div className="preview-facts">
            <div><span>Status</span><strong>{status}</strong></div>
            <div><span>Capacity</span><strong>{summary.capacity}</strong></div>
            <div><span>Max revenue</span><strong>{formatMoney(summary.revenue)}</strong></div>
          </div>
        </aside>
      </div>
    </div>
  );
}
