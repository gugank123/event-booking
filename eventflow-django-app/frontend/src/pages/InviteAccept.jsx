import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils/format';

export default function InviteAccept() {
  const { token } = useParams();
  const { user, token: authToken } = useAuth();
  const navigate = useNavigate();
  const [inv, setInv] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get(`/comms/invitations/${token}/`)
      .then((data) => setInv(data.invitation))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  async function respond(action) {
    if (!user) {
      navigate('/login', { state: { from: `/invite/${token}` } });
      return;
    }
    try {
      await api.post(`/comms/invitations/${token}/${action}/`, {}, authToken);
      if (action === 'accept') navigate(`/events/${inv.event}`);
      else navigate('/invitations');
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <div className="page">Loading invitation…</div>;
  if (error) return <div className="page">{error}</div>;
  if (!inv) return <div className="page">Invitation not found.</div>;

  const d = inv.event_detail;

  return (
    <div className="page page--narrow">
      <div className="invite-card invite-card--large">
        <span className="ticket-card__category">You're invited</span>
        <h1>{d.title}</h1>
        <p className="muted">
          {formatDate(d.starts_at)} · {d.venue}, {d.city}
        </p>
        {d.description && <p>{d.description}</p>}
        {inv.message && (
          <p className="muted">
            A note from the organiser: “{inv.message}”
          </p>
        )}
        <p>
          <span className={`status-pill status-pill--${inv.status === 'ACCEPTED' ? 'published' : inv.status === 'PENDING' ? 'draft' : 'cancelled'}`}>
            {inv.status}
          </span>
        </p>
        {inv.status === 'PENDING' ? (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn--primary" onClick={() => respond('accept')}>
              Accept & view event
            </button>
            <button className="btn btn--ghost" onClick={() => respond('decline')}>
              Decline
            </button>
          </div>
        ) : (
          <Link className="btn btn--primary" to={`/events/${inv.event}`}>
            View event
          </Link>
        )}
        <p className="muted" style={{ marginTop: '1rem' }}>
          Accepting takes you to the event page — no seat is booked automatically.
        </p>
      </div>
    </div>
  );
}
