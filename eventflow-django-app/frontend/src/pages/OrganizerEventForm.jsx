import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api, API_ORIGIN } from '../api/client';
import { useAuth } from '../context/AuthContext';

const FALLBACK_CATEGORIES = ['Music', 'Conference', 'Comedy', 'Sports', 'Theatre', 'Food & Drink', 'Outdoors', 'Workshop', 'Other'];

function emptyTicketType() {
  return { key: crypto.randomUUID(), name: '', price: '', quantity_total: '', max_per_user: '8', sale_start: '', sale_end: '' };
}

function emptySection() {
  return { key: crypto.randomUUID(), name: '', price: '', rows: '', seats_per_row: '' };
}

function toLocal(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toISO(local) {
  return local ? new Date(local).toISOString() : null;
}

export default function OrganizerEventForm() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;
  const isAdmin = user?.role === 'admin';

  const [categories, setCategories] = useState(FALLBACK_CATEGORIES);
  const [loading, setLoading] = useState(isEdit);
  const [title, setTitle] = useState('');
  const [shortDescription, setShortDescription] = useState('');
  const [category, setCategory] = useState('Music');
  const [customCategory, setCustomCategory] = useState('');
  const [organizerContact, setOrganizerContact] = useState('');
  const [venue, setVenue] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [stateName, setStateName] = useState('');
  const [pincode, setPincode] = useState('');
  const [mapLink, setMapLink] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [bookingOpens, setBookingOpens] = useState('');
  const [bookingCloses, setBookingCloses] = useState('');
  const [description, setDescription] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState('');
  const [status, setStatus] = useState('published');
  const [isFeatured, setIsFeatured] = useState(false);
  const [seatingType, setSeatingType] = useState('general');
  const [ticketTypes, setTicketTypes] = useState([emptyTicketType()]);
  const [sections, setSections] = useState([emptySection()]);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .get('/events/categories/')
      .then((data) => setCategories([...new Set([...FALLBACK_CATEGORIES, ...(data.categories || [])])]))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!isEdit) return;
    api
      .get(`/events/${id}/`, token)
      .then((data) => {
        const e = data.event;
        setTitle(e.title || '');
        setShortDescription(e.short_description || '');
        setCategory(e.category || 'Music');
        setOrganizerContact(e.organizer_contact || '');
        setVenue(e.venue || '');
        setAddress(e.address || '');
        setCity(e.city || '');
        setStateName(e.state || '');
        setPincode(e.pincode || '');
        setMapLink(e.map_link || '');
        setStartsAt(toLocal(e.starts_at));
        setEndsAt(toLocal(e.ends_at));
        setBookingOpens(toLocal(e.booking_opens_at));
        setBookingCloses(toLocal(e.booking_closes_at));
        setDescription(e.description || '');
        setImageUrl(e.image_url || '');
        setStatus(e.status || 'published');
        setIsFeatured(!!e.is_featured);
        setSeatingType(e.seating_type || 'general');
        if (e.ticket_types?.length) {
          setTicketTypes(
            e.ticket_types.map((t) => ({
              key: crypto.randomUUID(),
              id: t.id,
              name: t.name,
              price: t.price,
              quantity_total: t.quantity_total,
              max_per_user: t.max_per_user ?? '8',
              sale_start: toLocal(t.sale_start),
              sale_end: toLocal(t.sale_end)
            }))
          );
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, isEdit, token]);

  useEffect(() => {
    if (!imageFile) {
      setImagePreview('');
      return;
    }
    const url = URL.createObjectURL(imageFile);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [imageFile]);

  function updateTicketType(key, field, value) {
    setTicketTypes((rows) => rows.map((r) => (r.key === key ? { ...r, [field]: value } : r)));
  }

  function updateSection(key, field, value) {
    setSections((rows) => rows.map((r) => (r.key === key ? { ...r, [field]: value } : r)));
  }

  function validate() {
    const fe = {};
    if (!title.trim()) fe.title = 'Title cannot be empty.';
    if (!description.trim()) fe.description = 'Description cannot be empty.';
    if (!venue.trim()) fe.venue = 'Venue is required.';
    if (!city.trim()) fe.city = 'City is required.';
    if (!startsAt) fe.startsAt = 'Start time is required.';
    if (startsAt && endsAt && new Date(endsAt) <= new Date(startsAt)) fe.endsAt = 'End time must be after start time.';
    if (bookingOpens && bookingCloses && new Date(bookingCloses) <= new Date(bookingOpens))
      fe.bookingCloses = 'Booking closing must be after booking opening.';
    if (bookingCloses && startsAt && new Date(bookingCloses) > new Date(startsAt))
      fe.bookingCloses = 'Booking cannot close after the event starts.';
    ticketTypes.forEach((t, i) => {
      if (!t.name.trim()) fe[`ticket_${i}_name`] = 'Name required.';
      if (!(Number(t.price) >= 0) || t.price === '') fe[`ticket_${i}_price`] = 'Price cannot be negative.';
      if (!(Number(t.quantity_total) >= 1)) fe[`ticket_${i}_qty`] = 'Quantity must be at least 1.';
      if (Number(t.max_per_user) < 1) fe[`ticket_${i}_max`] = 'Allow at least 1 per user.';
      if (Number(t.max_per_user) > Number(t.quantity_total))
        fe[`ticket_${i}_max`] = 'Cannot exceed total tickets.';
    });
    if (seatingType === 'reserved') {
      sections.forEach((s, i) => {
        if (!s.name.trim()) fe[`sec_${i}_name`] = 'Section name required.';
        if (!(Number(s.price) >= 0) || s.price === '') fe[`sec_${i}_price`] = 'Price cannot be negative.';
        if (!s.rows.trim()) fe[`sec_${i}_rows`] = 'e.g. A,B for rows A-B.';
        if (!(Number(s.seats_per_row) >= 1)) fe[`sec_${i}_spr`] = 'Seats per row must be at least 1.';
      });
    }
    setFieldErrors(fe);
    return fe;
  }

  async function uploadImage(eventId) {
    if (!imageFile) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(imageFile.type)) {
      throw new Error('Poster must be JPG, PNG or WebP.');
    }
    if (imageFile.size > 5 * 1024 * 1024) {
      throw new Error('Poster must be 5 MB or smaller.');
    }
    const form = new FormData();
    form.append('image', imageFile);
    const res = await fetch(`${API_ORIGIN}/api/events/${eventId}/image/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || 'Poster upload failed.');
    }
  }

  async function saveWithStatus(nextStatus) {
    setError('');
    const fe = validate();
    if (Object.keys(fe).length > 0) {
      setError('Please fix the highlighted fields.');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return null;
    }
    setSubmitting(true);
    try {
      const effectiveCategory = category === '__custom' ? customCategory.trim() : category;
      const payload = {
        title: title.trim(),
        short_description: shortDescription.trim(),
        category: effectiveCategory,
        organizer_contact: organizerContact.trim(),
        venue: venue.trim(),
        address: address.trim(),
        city: city.trim(),
        state: stateName.trim(),
        pincode: pincode.trim(),
        map_link: mapLink.trim(),
        starts_at: toISO(startsAt),
        ends_at: toISO(endsAt) || toISO(startsAt),
        booking_opens_at: toISO(bookingOpens),
        booking_closes_at: toISO(bookingCloses),
        description: description.trim(),
        image_url: imageUrl.trim(),
        seating_type: seatingType,
        status: nextStatus,
        is_featured: isAdmin ? isFeatured : false
      };
      let eventId = id;
      if (isEdit) {
        const data = await api.put(`/events/${id}/`, payload, token);
        eventId = data.event.id;
      } else {
        const data = await api.post(
          '/events/',
          {
            ...payload,
            ticket_types: ticketTypes.map((t) => ({
              name: t.name.trim(),
              price: Number(t.price),
              quantity_total: Number(t.quantity_total),
              max_per_user: Number(t.max_per_user) || 8,
              sale_start: toISO(t.sale_start),
              sale_end: toISO(t.sale_end)
            }))
          },
          token
        );
        eventId = data.event.id;
      }
      await uploadImage(eventId);
      if (seatingType === 'reserved') {
        await api.post(
          `/events/${eventId}/seats/`,
          {
            sections: sections.map((s) => ({
              name: s.name.trim(),
              price: Number(s.price),
              rows: s.rows.split(',').map((r) => r.trim()).filter(Boolean),
              seats_per_row: Number(s.seats_per_row)
            }))
          },
          token
        ).catch((err) => {
          throw new Error(`Event saved, but seating failed: ${err.message}`);
        });
      }
      return eventId;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page">
      <h1>{isEdit ? 'Edit event post' : 'Create an event post'}</h1>
      <p className="muted">Sections 1–6 · Save a draft any time, preview it, then publish when ready.</p>

      <div className="create-layout">
        <motion.div
          className="form"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h3 className="form-section-title">1 · Event information</h3>
          <label>
            Event title
            <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} placeholder="e.g. Neon Pulse: Synthwave Night" />
            {fieldErrors.title && <span className="field-error">{fieldErrors.title}</span>}
          </label>
          <label>
            Short description <span className="muted">(one line, shown on cards)</span>
            <input value={shortDescription} onChange={(e) => setShortDescription(e.target.value)} maxLength={300} />
          </label>
          <div className="form-row">
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
                <option value="__custom">+ New category…</option>
              </select>
            </label>
            {category === '__custom' && (
              <label>
                Your category
                <input value={customCategory} onChange={(e) => setCustomCategory(e.target.value)} maxLength={60} />
              </label>
            )}
          </div>
          <label>
            Organizer name / contact
            <input value={organizerContact} onChange={(e) => setOrganizerContact(e.target.value)} maxLength={200} placeholder="e.g. Pulse Events · hello@pulse.events · +1 555-0100" />
          </label>
          <label>
            Full description
            <textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What happens, who it's for, what to expect…" />
            {fieldErrors.description && <span className="field-error">{fieldErrors.description}</span>}
          </label>

          <h3 className="form-section-title">2 · Event poster</h3>
          <label>
            Upload poster <span className="muted">(JPG/PNG/WebP, max 5 MB)</span>
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setImageFile(e.target.files[0] || null)} />
          </label>
          {(imagePreview || imageUrl) && (
            <img
              className="poster-preview"
              src={imagePreview || imageUrl}
              alt="Poster preview"
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
          )}
          <label>
            …or image URL
            <input type="url" value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="https://…" />
          </label>

          <h3 className="form-section-title">3 · Date & time</h3>
          <div className="form-row">
            <label>
              Starts at
              <input type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} />
              {fieldErrors.startsAt && <span className="field-error">{fieldErrors.startsAt}</span>}
            </label>
            <label>
              Ends at <span className="muted">(optional)</span>
              <input type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} />
              {fieldErrors.endsAt && <span className="field-error">{fieldErrors.endsAt}</span>}
            </label>
          </div>
          <div className="form-row">
            <label>
              Booking opens <span className="muted">(optional)</span>
              <input type="datetime-local" value={bookingOpens} onChange={(e) => setBookingOpens(e.target.value)} />
            </label>
            <label>
              Booking closes <span className="muted">(optional)</span>
              <input type="datetime-local" value={bookingCloses} onChange={(e) => setBookingCloses(e.target.value)} />
              {fieldErrors.bookingCloses && <span className="field-error">{fieldErrors.bookingCloses}</span>}
            </label>
          </div>

          <h3 className="form-section-title">4 · Venue</h3>
          <div className="form-row">
            <label>
              Venue name
              <input value={venue} onChange={(e) => setVenue(e.target.value)} maxLength={200} />
              {fieldErrors.venue && <span className="field-error">{fieldErrors.venue}</span>}
            </label>
            <label>
              City
              <input value={city} onChange={(e) => setCity(e.target.value)} maxLength={120} />
              {fieldErrors.city && <span className="field-error">{fieldErrors.city}</span>}
            </label>
          </div>
          <label>
            Street address
            <input value={address} onChange={(e) => setAddress(e.target.value)} maxLength={300} placeholder="e.g. 1200 Riverside Dr" />
          </label>
          <div className="form-row">
            <label>
              State
              <input value={stateName} onChange={(e) => setStateName(e.target.value)} maxLength={120} />
            </label>
            <label>
              Pincode
              <input value={pincode} onChange={(e) => setPincode(e.target.value)} maxLength={20} />
            </label>
          </div>
          <label>
            Google Maps / location link <span className="muted">(optional)</span>
            <input type="url" value={mapLink} onChange={(e) => setMapLink(e.target.value)} placeholder="https://maps.google.com/…" />
          </label>

          <h3 className="form-section-title">5 · Ticket information</h3>
          {!isEdit && (
            <fieldset className="ticket-type-builder">
              <legend>Ticket types (at least one)</legend>
              {ticketTypes.map((t, i) => (
                <div key={t.key}>
                  <div className="ticket-type-row">
                    <input placeholder="Name (e.g. VIP)" value={t.name} onChange={(e) => updateTicketType(t.key, 'name', e.target.value)} />
                    <input placeholder="Price" type="number" min="0" step="0.01" value={t.price} onChange={(e) => updateTicketType(t.key, 'price', e.target.value)} />
                    <input placeholder="Total tickets" type="number" min="1" value={t.quantity_total} onChange={(e) => updateTicketType(t.key, 'quantity_total', e.target.value)} />
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => setTicketTypes((rows) => (rows.length > 1 ? rows.filter((r) => r.key !== t.key) : rows))} aria-label="Remove ticket type">✕</button>
                  </div>
                  <div className="ticket-type-row ticket-type-row--sub">
                    <input placeholder="Max per user" type="number" min="1" value={t.max_per_user} onChange={(e) => updateTicketType(t.key, 'max_per_user', e.target.value)} />
                    <input type="datetime-local" title="Sale starts" value={t.sale_start} onChange={(e) => updateTicketType(t.key, 'sale_start', e.target.value)} />
                    <input type="datetime-local" title="Sale ends" value={t.sale_end} onChange={(e) => updateTicketType(t.key, 'sale_end', e.target.value)} />
                  </div>
                  {(fieldErrors[`ticket_${i}_name`] || fieldErrors[`ticket_${i}_price`] || fieldErrors[`ticket_${i}_qty`] || fieldErrors[`ticket_${i}_max`]) && (
                    <span className="field-error">
                      {[fieldErrors[`ticket_${i}_name`], fieldErrors[`ticket_${i}_price`], fieldErrors[`ticket_${i}_qty`], fieldErrors[`ticket_${i}_max`]].filter(Boolean).join(' ')}
                    </span>
                  )}
                </div>
              ))}
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => setTicketTypes((rows) => [...rows, emptyTicketType()])}>
                + Add another ticket type
              </button>
            </fieldset>
          )}
          {isEdit && <p className="muted">Ticket types are fixed after creation — manage availability from the event dashboard.</p>}

          <h3 className="form-section-title">6 · Seating configuration</h3>
          <fieldset className="role-choice">
            <legend>Seating type</legend>
            <label className={`role-option ${seatingType === 'general' ? 'is-selected' : ''}`}>
              <input type="radio" name="seating" value="general" checked={seatingType === 'general'} onChange={() => setSeatingType('general')} />
              General admission — no seat map, quantity booking
            </label>
            <label className={`role-option ${seatingType === 'reserved' ? 'is-selected' : ''}`}>
              <input type="radio" name="seating" value="reserved" checked={seatingType === 'reserved'} onChange={() => setSeatingType('reserved')} />
              Reserved seating — attendees pick exact seats
            </label>
          </fieldset>
          {seatingType === 'reserved' && (
            <fieldset className="ticket-type-builder">
              <legend>Sections & rows (e.g. VIP ₹1500, rows A-B)</legend>
              {sections.map((s, i) => (
                <div key={s.key}>
                  <div className="ticket-type-row">
                    <input placeholder="Section (e.g. VIP)" value={s.name} onChange={(e) => updateSection(s.key, 'name', e.target.value)} />
                    <input placeholder="Price" type="number" min="0" step="0.01" value={s.price} onChange={(e) => updateSection(s.key, 'price', e.target.value)} />
                    <input placeholder="Rows (A,B)" value={s.rows} onChange={(e) => updateSection(s.key, 'rows', e.target.value)} />
                    <input placeholder="Seats/row" type="number" min="1" value={s.seats_per_row} onChange={(e) => updateSection(s.key, 'seats_per_row', e.target.value)} />
                  </div>
                  {(fieldErrors[`sec_${i}_name`] || fieldErrors[`sec_${i}_price`] || fieldErrors[`sec_${i}_rows`] || fieldErrors[`sec_${i}_spr`]) && (
                    <span className="field-error">
                      {[fieldErrors[`sec_${i}_name`], fieldErrors[`sec_${i}_price`], fieldErrors[`sec_${i}_rows`], fieldErrors[`sec_${i}_spr`]].filter(Boolean).join(' ')}
                    </span>
                  )}
                </div>
              ))}
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSections((rows) => [...rows, emptySection()])}>
                + Add section
              </button>
            </fieldset>
          )}

          {isAdmin && (
            <>
              <h3 className="form-section-title">7 · Publishing</h3>
              <label className="check-row">
                <input type="checkbox" checked={isFeatured} onChange={(e) => setIsFeatured(e.target.checked)} />
                Feature on the homepage spotlight
              </label>
            </>
          )}

          {error && <p className="form-error">{error}</p>}
          <div className="form-actions">
            <button type="button" className="btn btn--ghost" disabled={submitting} onClick={async () => {
              const eventId = await saveWithStatus('draft');
              if (eventId) navigate(`/organizer/events/${eventId}`);
            }}>
              {submitting ? 'Saving…' : 'Save draft'}
            </button>
            <button type="button" className="btn btn--ghost" disabled={submitting} onClick={async () => {
              const eventId = await saveWithStatus(isEdit ? status : 'draft');
              if (eventId) navigate(`/organizer/events/${eventId}/preview`);
            }}>
              Preview
            </button>
            <button type="button" className="btn btn--primary" disabled={submitting} onClick={async () => {
              const eventId = await saveWithStatus('published');
              if (eventId) navigate(`/events/${eventId}`);
            }}>
              {submitting ? 'Publishing…' : 'Publish event'}
            </button>
          </div>
        </motion.div>

        <aside className="preview-pane">
          <h3 className="form-section-title">Live preview</h3>
          <p className="muted">How the card looks while you type. Full-page preview is one click away.</p>
        </aside>
      </div>
    </div>
  );
}
