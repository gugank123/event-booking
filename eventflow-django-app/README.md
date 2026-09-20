# EventFlow (Django + React edition)

The same ticketing/booking platform as before, rebuilt with:

- **Backend:** Django + Django REST Framework, JWT auth
  (`djangorestframework-simplejwt`), SQLite (a real SQL database, zero setup
  — swap the one `DATABASES` block in `settings.py` for Postgres/MySQL
  whenever you're ready).
- **Frontend:** React + Vite, React Router, plain CSS (unchanged design —
  same ticket-stub visual style as the Node version).
- **Payments:** simulated checkout only, same as before — the API validates
  that a card looks card-shaped and always "succeeds."

Two folders, two separate things to run:

```
backend/     <- Django API (run this first)
frontend/    <- React app (talks to the API)
```

## 1. Backend setup

Needs Python 3.10+.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env             # edit DJANGO_SECRET_KEY before deploying anywhere real
python manage.py migrate
python manage.py seed_demo       # creates demo accounts + sample events
python manage.py runserver       # http://localhost:8000
```

Demo accounts (password for all: `password123`):

| Role      | Email                    |
|-----------|--------------------------|
| Admin     | admin@eventflow.dev      |
| Organizer | organizer@eventflow.dev  |
| Attendee  | attendee@eventflow.dev   |

Django's own admin site is also live at `http://localhost:8000/admin/`
(log in with the admin account above) if you want to inspect or edit data
directly.

## 2. Frontend setup

In a second terminal:

```bash
cd frontend
cp .env.example .env             # points at http://localhost:8000/api by default
npm install
npm run dev                       # http://localhost:5173
```

Open http://localhost:5173.

## Project layout

```
backend/
  eventflow/          # project settings, root urls, admin-only API views
  accounts/            # custom User model (role field), register/login/me
  events/              # Event + TicketType models, CRUD, search
  bookings/            # Booking model, checkout, cancel
  requirements.txt

frontend/
  src/
    pages/             # one file per route (Login, Register, Home, ...)
    components/         # Navbar, EventCard, ProtectedRoute
    context/AuthContext.jsx
    api/client.js        # fetch wrapper, attaches the JWT
    styles/index.css
```

## What's included

- **Auth:** email + password login and signup, JWT sessions
  (`/api/auth/register/`, `/api/auth/login/`), role chosen at signup
  (attendee or organizer — admin is granted through Django admin or the
  in-app admin panel, never self-assigned).
- **Attendees:** browse/search/filter published events, pick a ticket type
  and quantity, run through a simulated checkout, view and cancel their own
  bookings.
- **Organizers:** create events with one or more ticket types, see a live
  attendee roster and revenue per event, cancel an event.
- **Admins:** platform-wide stats, promote/suspend users, cancel or restore
  any event.

## Notes on the rebuild

- Auth is by email. The custom `User` model (in `accounts/models.py`) keeps
  Django's built-in `username` field internally (set to the email at signup)
  so no custom user manager is needed, but every login/registration call
  uses `email`.
- A suspended user re-uses Django's built-in `is_active` flag rather than a
  separate status field — Django already refuses to authenticate inactive
  users everywhere, so this "just works."
- Every DRF validation error is flattened into the same `{"error": "..."}`
  shape (see `eventflow/exceptions.py`) so the frontend's error handling
  doesn't need to know or care whether a given endpoint is Node or Django.

## Deploying

- **Backend:** any host that runs Python (Render, Railway, Fly.io, a VPS).
  Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS`, and
  `CORS_ALLOWED_ORIGINS` (your deployed frontend's URL) as environment
  variables. Point `DATABASES` at a managed Postgres instance instead of
  SQLite once you're past local development — most hosts wipe local disk
  between deploys, which would erase a SQLite file.
- **Frontend:** any static host (Vercel, Netlify, Cloudflare Pages). Run
  `npm run build` and deploy the `dist/` folder, with `VITE_API_URL` set to
  your deployed backend's `/api` URL at build time.

## Going further

- **Real payments:** replace the validation in `bookings/serializers.py`
  (`CheckoutSerializer`) with a real Stripe PaymentIntent confirmation
  before marking a booking `confirmed`.
- **Email:** send booking confirmations after checkout instead of only
  showing the reference in-app.
- **Token refresh:** the frontend currently stores the JWT access/refresh
  pair but only uses the access token; wire up `/api/auth/token/refresh/`
  if you want sessions to survive past the access token's lifetime
  (currently 1 day) without a full re-login.
