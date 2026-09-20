import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

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
        {user?.role === 'organizer' && <Link to="/organizer">Manage events</Link>}
        {user?.role === 'admin' && <Link to="/admin">Admin</Link>}
        {user && <Link to="/my-bookings">My tickets</Link>}
      </nav>
      <div className="navbar__actions">
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
