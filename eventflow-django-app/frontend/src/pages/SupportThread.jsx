import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils/format';

export default function SupportThread() {
  const { id } = useParams();
  const { token } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  function load() {
    api
      .get(`/comms/support/${id}/`, token)
      .then((data) => {
        setTicket(data.ticket);
        setMessages(data.messages);
        setError('');
      })
      .catch((err) => setError(err.message));
  }

  useEffect(load, [id, token]);

  async function handleReply(e) {
    e.preventDefault();
    setError('');
    setSending(true);
    try {
      await api.post(`/comms/support/${id}/`, { body }, token);
      setBody('');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  if (error && !ticket) return <div className="page">{error}</div>;
  if (!ticket) return <div className="page">Loading…</div>;

  const closed = ticket.status === 'CLOSED';

  return (
    <div className="page page--narrow">
      <Link to="/support" className="muted">
        ← All tickets
      </Link>
      <h1>
        #{ticket.id} · {ticket.subject}
      </h1>
      <p className="muted">
        {ticket.category} · {ticket.priority} priority · {ticket.status.replace(/_/g, ' ')} · opened{' '}
        {formatDate(ticket.created_at)}
      </p>
      <div className="thread">
        <div className="bubble is-mine">
          <div className="bubble__head">
            <strong>You</strong>
            <span className="muted">{formatDate(ticket.created_at)}</span>
          </div>
          <p>{ticket.description}</p>
        </div>
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.mine ? 'is-mine' : 'is-theirs'}`}>
            <div className="bubble__head">
              <strong>{m.sender_name}</strong>
              <span className="muted">{formatDate(m.created_at)}</span>
            </div>
            <p>{m.body}</p>
          </div>
        ))}
      </div>
      {error && <p className="form-error">{error}</p>}
      {!closed ? (
        <form className="form" onSubmit={handleReply} style={{ marginTop: '1rem' }}>
          <textarea required value={body} onChange={(e) => setBody(e.target.value)} rows={3} placeholder="Write a reply…" />
          <button className="btn btn--primary" type="submit" disabled={sending}>
            {sending ? 'Sending…' : 'Send reply'}
          </button>
        </form>
      ) : (
        <p className="muted" style={{ marginTop: '1rem' }}>
          This ticket is closed.
        </p>
      )}
    </div>
  );
}
