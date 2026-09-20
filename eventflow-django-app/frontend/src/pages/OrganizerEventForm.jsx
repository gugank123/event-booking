import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

const CATEGORY_OPTIONS = ['Music', 'Conference', 'Comedy', 'Sports', 'Theatre', 'Workshop', 'Other'];

function emptyTicketType() {
  return { key: crypto.randomUUID(), name: '', price: '', quantity_total: '' };
}

export default function OrganizerEventForm() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [category, setCategory] = useState(CATEGORY_OPTIONS[0]);
  const [venue, setVenue] = useState('');
  const [city, setCity] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [description, setDescription] = useState('');
  const [ticketTypes, setTicketTypes] = useState([emptyTicketType()]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function updateTicketType(key, field, value) {
    setTicketTypes((rows) => rows.map((r) => (r.key === key ? { ...r, [field]: value } : r)));
  }

  function addTicketType() {
    setTicketTypes((rows) => [...rows, emptyTicketType()]);
  }

  function removeTicketType(key) {
    setTicketTypes((rows) => (rows.length > 1 ? rows.filter((r) => r.key !== key) : rows));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const payload = {
        title,
        category,
        venue,
        city,
        starts_at: new Date(startsAt).toISOString(),
        ends_at: endsAt ? new Date(endsAt).toISOString() : new Date(startsAt).toISOString(),
        description,
        ticket_types: ticketTypes.map((t) => ({
          name: t.name,
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

  return (
    <div className="page page--narrow">
      <h1>Create an event</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label>
          Title
          <input required value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <div className="form-row">
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label>
            City
            <input required value={city} onChange={(e) => setCity(e.target.value)} />
          </label>
        </div>
        <label>
          Venue
          <input required value={venue} onChange={(e) => setVenue(e.target.value)} />
        </label>
        <div className="form-row">
          <label>
            Starts at
            <input required type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} />
          </label>
          <label>
            Ends at (optional)
            <input type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} />
          </label>
        </div>
        <label>
          Description
          <textarea rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>

        <fieldset className="ticket-type-builder">
          <legend>Ticket types</legend>
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
                className="btn btn--ghost btn--icon"
                onClick={() => removeTicketType(t.key)}
                aria-label="Remove ticket type"
              >
                ✕
              </button>
            </div>
          ))}
          <button type="button" className="btn btn--ghost" onClick={addTicketType}>
            + Add another ticket type
          </button>
        </fieldset>

        {error && <p className="form-error">{error}</p>}
        <button className="btn btn--primary" type="submit" disabled={submitting}>
          {submitting ? 'Publishing…' : 'Publish event'}
        </button>
      </form>
    </div>
  );
}
