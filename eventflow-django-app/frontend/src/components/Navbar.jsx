import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import NotificationBell from './NotificationBell';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/');
  }

  return (
    <header className="navbar">
      <Link to="/" className="navbar__brand">
        EventFlow
      </Link>
      <nav className="navbar__links">
        <Link to="/">Browse</Link>
        <Link to="/post-event">＋ Post an event</Link>
        {(user?.role === 'organizer' || user?.role === 'admin') && <Link to="/organizer">Manage events</Link>}
        {user?.role === 'admin' && <Link to="/admin">Admin</Link>}
        {user && <Link to="/my-bookings">My tickets</Link>}
        {user && <Link to="/wishlist">Wishlist</Link>}
        {user && <Link to="/messages">Messages</Link>}
        <Link to="/help">Help</Link>
      </nav>
      <div className="navbar__actions">
        {user && <NotificationBell />}
        {user ? (
          <>
            <span className="navbar__user">{user.name}</span>
            <button className="btn btn--ghost" onClick={handleLogout}>
              Log out
            </button>
          </>
        ) : (
          <>
            <Link className="btn btn--ghost" to="/login">
              Log in
            </Link>
            <Link className="btn btn--primary" to="/register">
              Sign up
            </Link>
          </>
        )}
      </div>
    </header>
  );
}
