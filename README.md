# Event Ticketing & Seat Booking Platform

A full-stack web application built with **Python + Django**. This is the **Week 1**
foundation of the capstone project: a working Django project with an `events` app,
an `Event` model backed by SQLite, Django Admin CRUD, and a dynamic event listing page.

## Features (Week 1)

- Django project + `events` app
- `Event` model (title, description, category, date, time, venue, price, created_at)
- Django Admin to create / edit / delete events
- Event listing page driven by the database (no hardcoded data)
- Friendly empty-state message: *"No upcoming events available."*
- SQLite development database
- Unit tests covering the model and the listing page

## Project Structure

```
event_booking/
├── manage.py
├── requirements.txt
├── .gitignore
├── event_booking/          # project settings / urls
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── events/                 # events app
│   ├── migrations/
│   ├── templates/events/
│   │   └── event_list.html
│   ├── management/commands/
│   │   └── load_sample_data.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
└── venv/                   # virtual environment (not committed to git)
```

## Setup (first time)

Run all commands from the `event_booking` folder.

```bash
# 1. Create the virtual environment (one time)
python -m venv venv

# 2. Activate it
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install Django
pip install -r requirements.txt

# 4. Create the database tables
python manage.py migrate

# 5. Create an admin superuser (enter a username, email, password)
python manage.py createsuperuser

# 6. (Optional) Load the 3 sample events
python manage.py load_sample_data

# 7. Run the server
python manage.py runserver
```

Open:
- **Event listing page:** http://127.0.0.1:8000/
- **Django Admin:** http://127.0.0.1:8000/admin/

## Useful Commands

| Task | Command |
| --- | --- |
| Create a new migration | `python manage.py makemigrations` |
| Apply migrations | `python manage.py migrate` |
| Load sample data | `python manage.py load_sample_data` |
| Run the test suite | `python manage.py test` |
| Start the server | `python manage.py runserver` |

## Sample Events

| Title | Category | Date | Time | Venue | Price |
| --- | --- | --- | --- | --- | --- |
| Tech Innovators Conference 2026 | Technology | 2026-09-15 | 10:00 AM | JJCET Auditorium | Rs. 500 |
| Campus Music Festival 2026 | Music | 2026-09-20 | 6:00 PM | College Open Ground | Rs. 300 |
| Entrepreneurship Summit 2026 | Business | 2026-09-25 | 9:30 AM | Seminar Hall | Rs. 400 |

## What Comes Later (Future Weeks)

Authentication, venues, seat layouts, seat selection, booking system,
booking history, cancellation, payments, QR codes, and cloud deployment.

## Tech Stack

- Python 3.14, Django 6.x
- Django ORM + SQLite (development)
- Bootstrap 5 (CDN)
- Git / GitHub
