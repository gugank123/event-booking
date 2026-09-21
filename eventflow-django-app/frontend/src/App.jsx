import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import EventDetail from './pages/EventDetail';
import MyBookings from './pages/MyBookings';
import Wishlist from './pages/Wishlist';
import OrganizerDashboard from './pages/OrganizerDashboard';
import OrganizerEventForm from './pages/OrganizerEventForm';
import OrganizerEventBookings from './pages/OrganizerEventBookings';
import AdminDashboard from './pages/AdminDashboard';
import Notifications from './pages/Notifications';
import Messages from './pages/Messages';
import ConversationThread from './pages/ConversationThread';
import Invitations from './pages/Invitations';
import InviteAccept from './pages/InviteAccept';
import Help from './pages/Help';
import Support from './pages/Support';
import SupportThread from './pages/SupportThread';
import PostEvent from './pages/PostEvent';

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/events/:id" element={<EventDetail />} />
          <Route
            path="/my-bookings"
            element={
              <ProtectedRoute>
                <MyBookings />
              </ProtectedRoute>
            }
          />
          <Route
            path="/wishlist"
            element={
              <ProtectedRoute>
                <Wishlist />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notifications"
            element={
              <ProtectedRoute>
                <Notifications />
              </ProtectedRoute>
            }
          />
          <Route
            path="/messages"
            element={
              <ProtectedRoute>
                <Messages />
              </ProtectedRoute>
            }
          />
          <Route
            path="/messages/:id"
            element={
              <ProtectedRoute>
                <ConversationThread />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invitations"
            element={
              <ProtectedRoute>
                <Invitations />
              </ProtectedRoute>
            }
          />
          <Route path="/invite/:token" element={<InviteAccept />} />
          <Route path="/help" element={<Help />} />
          <Route path="/post-event" element={<PostEvent />} />
          <Route
            path="/support"
            element={
              <ProtectedRoute>
                <Support />
              </ProtectedRoute>
            }
          />
          <Route
            path="/support/:id"
            element={
              <ProtectedRoute>
                <SupportThread />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizer"
            element={
              <ProtectedRoute roles={['organizer', 'admin']}>
                <OrganizerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizer/new"
            element={
              <ProtectedRoute roles={['organizer', 'admin']}>
                <OrganizerEventForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizer/events/:id"
            element={
              <ProtectedRoute roles={['organizer', 'admin']}>
                <OrganizerEventBookings />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
    </div>
  );
}
