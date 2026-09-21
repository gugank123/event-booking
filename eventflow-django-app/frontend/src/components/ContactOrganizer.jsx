import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

const TOPICS = [
  { value: 'general', label: 'General enquiry' },
  { value: 'booking', label: 'Booking question' },
  { value: 'seat', label: 'Seat question' },
  { value: 'event_info', label: 'Event information' },
  { value: 'cancellation', label: 'Cancellation question' },
  { value: 'other', label: 'Other' }
];

/** "Contact Organizer" button + dialog. Auto-attaches event (and booking). */
export default function ContactOrganizer({ eventId, bookingId = null, eventTitle = '' }) {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('general');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  function openDialog() {
    if (!user) {
      navigate('/login');
      return;
    }
    setOpen(true);
  }

  async function handleSend(e) {
    e.preventDefault();
    setError('');
    setSending(true);
    try {
      const data = await api.post(
        '/comms/conversations/',
        { event_id: eventId, booking_id: bookingId, subject, topic, body },
        token
      );
      setOpen(false);
      navigate(`/messages/${data.conversation.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button className="btn btn--ghost btn--sm" onClick={openDialog}>
        ✉ Contact Organizer
      </button>
      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Contact the organizer</h2>
            {eventTitle && <p className="muted">About: {eventTitle}</p>}
            <form className="form" style={{ border: 'none', padding: 0, background: 'none' }} onSubmit={handleSend}>
              <label>
                Topic
                <select value={topic} onChange={(e) => setTopic(e.target.value)}>
                  {TOPICS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Subject
                <input required value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} />
              </label>
              <label>
                Message
                <textarea required value={body} onChange={(e) => setBody(e.target.value)} rows={4} />
              </label>
              {error && <p className="form-error">{error}</p>}
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn--primary" type="submit" disabled={sending}>
                  {sending ? 'Sending…' : 'Send message'}
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => setOpen(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
