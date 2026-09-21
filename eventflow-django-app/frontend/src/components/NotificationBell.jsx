import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

export function useUnreadCount() {
  const { token } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!token) {
      setUnread(0);
      return;
    }
    let cancelled = false;
    async function fetchCount() {
      try {
        const data = await api.get('/comms/notifications/unread-count/', token);
        if (!cancelled) setUnread(data.unread);
      } catch {
        /* badge stays stale rather than breaking nav */
      }
    }
    fetchCount();
    const timer = setInterval(fetchCount, 30000);
    window.addEventListener('eventflow:notifications-changed', fetchCount);
    return () => {
      cancelled = true;
      clearInterval(timer);
      window.removeEventListener('eventflow:notifications-changed', fetchCount);
    };
  }, [token]);

  return [unread, setUnread];
}

export function refreshNotifications() {
  window.dispatchEvent(new Event('eventflow:notifications-changed'));
}

export default function NotificationBell() {
  const { token } = useAuth();
  const [unread] = useUnreadCount();
  if (!token) return null;
  return (
    <Link to="/notifications" className="bell" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}>
      <span className="bell__icon">🔔</span>
      {unread > 0 && <span className="bell__badge">{unread > 99 ? '99+' : unread}</span>}
    </Link>
  );
}
