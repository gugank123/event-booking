import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils/format';
import { refreshNotifications } from '../components/NotificationBell';

export default function ConversationThread() {
  const { id } = useParams();
  const { user, token } = useAuth();
  const [conv, setConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  function load() {
    api
      .get(`/comms/conversations/${id}/`, token)
      .then((data) => {
        setConv(data.conversation);
        setMessages(data.messages);
        setError('');
        refreshNotifications();
      })
      .catch((err) => setError(err.message));
  }

  useEffect(load, [id, token]);

  async function handleReply(e) {
    e.preventDefault();
    setError('');
    setSending(true);
    try {
      await api.post(`/comms/conversations/${id}/`, { body }, token);
      setBody('');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function handleStatus(status) {
    try {
      const data = await api.post(`/comms/conversations/${id}/`, { action: 'status', status }, token);
      setConv(data.conversation);
    } catch (err) {
      setError(err.message);
    }
  }

  if (error && !conv) return <div className="page">{error}</div>;
  if (!conv) return <div className="page">Loading…</div>;

  const canManage = conv.organizer === user?.id || user?.role === 'admin';
  const closed = conv.status === 'CLOSED';

  return (
    <div className="page page--narrow">
      <Link to="/messages" className="muted">
        ← All messages
      </Link>
      <h1>
        #{conv.id} · {conv.subject}
      </h1>
      <p className="muted">
        {conv.customer_name} ↔ {conv.organizer_name}
        {conv.event_title ? ` · ${conv.event_title}` : ''} · {conv.topic.replace('_', ' ')} · {conv.status.replace('_', ' ')}
      </p>
      <div className="thread">
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
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button className="btn btn--primary" type="submit" disabled={sending}>
              {sending ? 'Sending…' : 'Send reply'}
            </button>
            {canManage && conv.status !== 'RESOLVED' && (
              <button type="button" className="btn btn--ghost" onClick={() => handleStatus('RESOLVED')}>
                Mark resolved
              </button>
            )}
            {(canManage || conv.customer === user?.id) && (
              <button type="button" className="btn btn--ghost" onClick={() => handleStatus('CLOSED')}>
                Close
              </button>
            )}
          </div>
        </form>
      ) : (
        <p className="muted" style={{ marginTop: '1rem' }}>
          This conversation is closed.
        </p>
      )}
    </div>
  );
}
