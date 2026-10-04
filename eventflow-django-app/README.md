# EventFlow (Django + React edition)

The same ticketing/booking platform as before, rebuilt with:

- **Backend:** Django + Django REST Framework, JWT auth
  (`djangorestframework-simplejwt`), MySQL (PyMySQL; `MYSQL_URL` or the
  `MYSQL_*` vars in `backend/.env`).
- **Frontend:** React + Vite, React Router, plain CSS (unchanged design —
  same ticket-stub visual style as the Node version).
- **Payments:** real Razorpay Checkout (UPI/cards/netbanking, INR) with
  server-side signature verification + idempotent webhook. Without gateway
  keys the API issues clearly-marked `order_TEST_*` orders for local flow
  testing — no fake "always succeeds" card charge remains.

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

- **Auth:** email + password login and signup with 6-digit email verification
  (hashed, expiring, rate-limited), JWT sessions with rotation + blacklist
  (`/api/auth/register/`, `/api/auth/verify-email/`, `/api/auth/login/`,
  `/api/auth/logout/`, `/api/auth/forgot-password/`,
  `/api/auth/reset-password/`), role chosen at signup
  (attendee or organizer — admin is granted through Django admin or the
  in-app admin panel, never self-assigned).
- **Attendees:** browse/search/filter published events, hold seats (8-min timer)
  or pick a quantity, apply coupons, pay via Razorpay, view QR tickets and pay
  pending bookings from My Bookings, cancel per policy with gateway refunds.
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

## Communications, support & invitations

Beyond booking, the platform now includes a full communication layer
(`backend/comms/`, mounted at `/api/comms/`):

- **Notification center** — every booking, event update, message, invitation
  and support reply creates an in-app notification. Bell icon with unread
  count in the navbar, `/notifications` page (filter unread, mark
  read/all-read, delete).
- **Organizer → attendees** — from an event's Manage page: post an
  **announcement** (in-app and/or email to all confirmed attendees) or send a
  **message broadcast**. Editing date/venue/city/status on an event
  automatically notifies confirmed attendees (in-app + email).
- **Customer → organizer** — "Contact Organizer" on every event page and
  booking auto-attaches the event/booking and opens a **conversation**
  (`OPEN → IN_PROGRESS → RESOLVED → CLOSED`). Both sides reply from
  `/messages`; organizers see customer threads there too.
- **Invitations** — organizers invite by email from the event Manage page.
  Guests get an email + in-app notification with a token link
  (`/invite/<token>/`); accepting opens the event page (no seat auto-booked).
- **Help Center** (`/help`) — searchable FAQs seeded by migration, support
  contact details from settings, links to tickets and reports.
- **Support tickets** (`/support`) — `OPEN → IN_PROGRESS → WAITING_FOR_USER →
  RESOLVED → CLOSED`, priorities, admin assignment, full reply history, email
  updates. Admins manage everything in Django admin too.
- **Reports** — users file event/organizer/booking/payment/technical reports;
  admins triage them in Django admin.
- **Email service** (`comms/emails.py` + `comms/templates/comms/emails/`) —
  templated text+HTML mail for welcome, booking confirmation/cancellation,
  invitations, announcements, organizer messages, support updates and event
  updates. Console backend by default; set `EMAIL_BACKEND` + SMTP vars for
  real mail. Mail failures never break requests.

### Extra environment variables

```
FRONTEND_URL=http://localhost:5173   # links inside emails
SUPPORT_EMAIL=support@eventflow.dev  # shown on Help page
SUPPORT_PHONE=                       # optional, shown on Help page
```

### Running & testing

```bash
cd backend
venv\Scripts\python manage.py migrate   # includes comms + FAQ seeds
venv\Scripts\python manage.py test      # 12 workflow tests (auth, booking, comms, IDOR)
```

Or double-click `start_app.bat` (starts MySQL if needed, Django, React, Chrome).

## Post Event (organizers)

Organizers post from **＋ Post an event** (navbar, homepage hero, or
`/organizer/new`). The form covers: basic info + organizer contact, poster
upload (JPG/PNG/WebP ≤ 5 MB) or image URL with preview, dates + booking
window, full venue (address/state/pincode/map link), ticket tiers (price,
quantity, per-user cap, sale window), and reserved-seating setup
(sections → rows × seats, e.g. VIP ₹1500 rows A-B).

Flow: **Save Draft → Preview** (pixel-identical event page with a back-to-edit
banner) **→ Publish**. Drafts are invisible publicly (list + direct URL 404
for outsiders). My Events (`/organizer`) shows image, stats, and actions:
View, Edit, Preview, Publish/Unpublish, Cancel, Duplicate, Delete draft
(deletion blocked while confirmed bookings exist). Date/venue/cancellation
edits auto-notify confirmed attendees (in-app + email).

Customers only ever see `published` events; booking enforces the booking
window, per-user caps, live availability (no overselling), and exact seat
picking for reserved events. Prices display in USD; seat labels and booking
emails adapt automatically.

```bash
cd backend
venv\Scripts\python manage.py seed_showcase   # 9 extra demo events + reviews
venv\Scripts\python manage.py test events     # 13 post-event workflow tests
```

## Going further

- **Docs:** live OpenAPI at `/api/docs/` (auth, holds, booking, Razorpay
  order/verify/webhook, tickets, coupons).
- **Background jobs:** `expire_holds`, `send_reminders`, `cleanup_auth`
  management commands — schedule them as cron (see `DEPLOY.md`).
- **Token refresh:** the frontend stores the JWT pair and silently refreshes
  the access token (60-min lifetime) via `/api/auth/token/refresh/`.
