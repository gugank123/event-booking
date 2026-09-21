import { useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

/** Organizer communicate hub: announcement, attendee message, invitation. */
export default function OrganizerComms({ eventId }) {
  const { token } = useAuth();
  const [tab, setTab] = useState('announce');
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState(false);

  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [sendEmail, setSendEmail] = useState(true);
  const [sendInApp, setSendInApp] = useState(true);

  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [emailAlso, setEmailAlso] = useState(true);

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteMsg, setInviteMsg] = useState('');
  const [inviteLink, setInviteLink] = useState('');

  async function submit(path, payload, success) {
    setError('');
    setOk('');
    setBusy(true);
    try {
      const data = await api.post(path, { event_id: eventId, ...payload }, token);
      setOk(success(data));
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h2>Communicate</h2>
      <div className="filter-row">
        {[
          ['announce', 'Announcement'],
          ['message', 'Message attendees'],
          ['invite', 'Invite guests']
        ].map(([v, label]) => (
          <button key={v} className={`chip ${tab === v ? 'is-active' : ''}`} onClick={() => setTab(v)}>
            {label}
          </button>
        ))}
      </div>

      {error && <p className="form-error">{error}</p>}
      {ok && <p className="form-ok">{ok}</p>}

      {tab === 'announce' && (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            submit('/comms/announcements/', { title, message, send_email: sendEmail, send_in_app: sendInApp }, (d) => {
              setTitle('');
              setMessage('');
              return `Announcement posted — ${d.notified} attendee(s) notified.`;
            });
          }}
        >
          <label>
            Title
            <input required value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} placeholder="e.g. Venue entrance changed to Gate B" />
          </label>
          <label>
            Message
            <textarea required value={message} onChange={(e) => setMessage(e.target.value)} rows={4} />
          </label>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <label style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
              <input type="checkbox" checked={sendInApp} onChange={(e) => setSendInApp(e.target.checked)} /> In-app
            </label>
            <label style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
              <input type="checkbox" checked={sendEmail} onChange={(e) => setSendEmail(e.target.checked)} /> Email
            </label>
          </div>
          <button className="btn btn--primary" type="submit" disabled={busy}>
            {busy ? 'Posting…' : 'Post announcement'}
          </button>
        </form>
      )}

      {tab === 'message' && (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            submit('/comms/broadcast/', { audience: 'event', subject, body, send_email: emailAlso }, (d) => {
              setSubject('');
              setBody('');
              return `Message sent to ${d.sent} attendee(s).`;
            });
          }}
        >
          <label>
            Subject
            <input required value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} placeholder="e.g. Your event starts tomorrow at 6 PM" />
          </label>
          <label>
            Message
            <textarea required value={body} onChange={(e) => setBody(e.target.value)} rows={4} />
          </label>
          <label style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
            <input type="checkbox" checked={emailAlso} onChange={(e) => setEmailAlso(e.target.checked)} /> Also send by email
          </label>
          <button className="btn btn--primary" type="submit" disabled={busy}>
            {busy ? 'Sending…' : 'Message all attendees'}
          </button>
        </form>
      )}

      {tab === 'invite' && (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            submit('/comms/invitations/', { email: inviteEmail, message: inviteMsg }, (d) => {
              const link = `${window.location.origin}/invite/${d.invitation.token}`;
              setInviteLink(link);
              setInviteEmail('');
              setInviteMsg('');
              return `Invitation sent to ${d.invitation.email}.`;
            });
          }}
        >
          <label>
            Guest email
            <input required type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
          </label>
          <label>
            Personal message (optional)
            <textarea value={inviteMsg} onChange={(e) => setInviteMsg(e.target.value)} rows={3} />
          </label>
          <button className="btn btn--primary" type="submit" disabled={busy}>
            {busy ? 'Sending…' : 'Send invitation'}
          </button>
          {inviteLink && (
            <p className="muted">
              Shareable link: <code>{inviteLink}</code>
            </p>
          )}
        </form>
      )}
    </section>
  );
}
