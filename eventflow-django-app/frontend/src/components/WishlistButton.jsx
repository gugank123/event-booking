import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

/** Heart toggle that saves/unsaves an event. Stops card-link navigation. */
export default function WishlistButton({ eventId, initial = false, inline = false, onChange }) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false);

  async function toggle(e) {
    e.preventDefault();
    e.stopPropagation();
    if (!token) {
      navigate('/login');
      return;
    }
    setBusy(true);
    try {
      if (saved) {
        await api.del(`/events/${eventId}/wishlist/`, token);
        setSaved(false);
        onChange?.(false);
      } else {
        await api.post(`/events/${eventId}/wishlist/`, {}, token);
        setSaved(true);
        onChange?.(true);
      }
    } catch {
      /* leave state as-is on failure */
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className={`wishlist-btn ${saved ? 'is-active' : ''} ${inline ? 'wishlist-btn--inline' : ''}`}
      onClick={toggle}
      disabled={busy}
      aria-label={saved ? 'Remove from wishlist' : 'Save to wishlist'}
      title={saved ? 'Saved' : 'Save for later'}
    >
      {saved ? '♥' : '♡'}
    </button>
  );
}
