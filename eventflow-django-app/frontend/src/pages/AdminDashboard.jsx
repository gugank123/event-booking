import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatMoney } from '../utils/format';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/api$/, '');

export default function AdminDashboard() {
  const { token, user } = useAuth();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [events, setEvents] = useState([]);
  const [tab, setTab] = useState('overview');
  const [error, setError] = useState('');

  function loadAll() {
    Promise.all([api.get('/admin/stats/', token), api.get('/admin/users/', token), api.get('/admin/events/', token)])
      .then(([s, u, e]) => {
        setStats(s);
        setUsers(u.users);
        setEvents(e.events);
      })
      .catch((err) => setError(err.message));
  }

  useEffect(loadAll, [token]);

  async function updateUser(id, patch) {
    try {
      await api.patch(`/admin/users/${id}/`, patch, token);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function updateEventStatus(id, status) {
    try {
      await api.put(`/events/${id}/`, { status }, token);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Admin</h1>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="btn btn--primary btn--sm" to="/organizer/new">
            ＋ Post event
          </Link>
          <Link className="btn btn--ghost btn--sm" to="/organizer">
            Manage events
          </Link>
          <a className="btn btn--ghost btn--sm" href={`${API_BASE}/admin/`} target="_blank" rel="noreferrer">
            Django admin ↗
          </a>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}

      <div className="filter-row">
        <button className={`chip ${tab === 'overview' ? 'is-active' : ''}`} onClick={() => setTab('overview')}>
          Overview
        </button>
        <button className={`chip ${tab === 'users' ? 'is-active' : ''}`} onClick={() => setTab('users')}>
          Users
        </button>
        <button className={`chip ${tab === 'events' ? 'is-active' : ''}`} onClick={() => setTab('events')}>
          Events
        </button>
      </div>

      {tab === 'overview' && stats && (
        <div className="stat-row">
          <div className="stat-card">
            <span className="stat-card__value">{stats.totalUsers}</span>
            <span className="stat-card__label">Users ({stats.attendees} attendees, {stats.organizers} organizers)</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__value">{stats.publishedEvents}</span>
            <span className="stat-card__label">Live events ({stats.totalEvents} total)</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__value">{stats.ticketsSold}</span>
            <span className="stat-card__label">Tickets sold</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__value">{formatMoney(stats.revenue)}</span>
            <span className="stat-card__label">Platform revenue</span>
          </div>
        </div>
      )}

      {tab === 'users' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Joined</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>
                  <select value={u.role} disabled={u.id === user.id} onChange={(e) => updateUser(u.id, { role: e.target.value })}>
                    <option value="attendee">Attendee</option>
                    <option value="organizer">Organizer</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td>
                  <span className={`status-pill status-pill--${u.status === 'active' ? 'confirmed' : 'cancelled'}`}>{u.status}</span>
                </td>
                <td>{formatDate(u.date_joined)}</td>
                <td>
                  {u.id !== user.id && (
                    <button
                      className="btn btn--ghost"
                      onClick={() => updateUser(u.id, { status: u.status === 'active' ? 'suspended' : 'active' })}
                    >
                      {u.status === 'active' ? 'Suspend' : 'Reactivate'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === 'events' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Event</th>
              <th>Organizer</th>
              <th>Status</th>
              <th>Tickets sold</th>
              <th>Revenue</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>
                  {e.title}
                  <div className="muted">{formatDate(e.startsAt)}</div>
                </td>
                <td>{e.organizerName}</td>
                <td>
                  <span className={`status-pill status-pill--${e.status === 'published' ? 'confirmed' : 'cancelled'}`}>{e.status}</span>
                </td>
                <td>{e.ticketsSold}</td>
                <td>{formatMoney(e.revenue)}</td>
                <td>
                  {e.status !== 'cancelled' ? (
                    <button className="btn btn--ghost" onClick={() => updateEventStatus(e.id, 'cancelled')}>
                      Cancel
                    </button>
                  ) : (
                    <button className="btn btn--ghost" onClick={() => updateEventStatus(e.id, 'published')}>
                      Restore
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
