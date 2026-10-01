# PulseTrack

PulseTrack is a responsive personal fitness log built with Flask, SQLAlchemy, server-rendered HTML, and modern CSS. Users can register, sign in, maintain a private workout history, search entries, and use JSON API endpoints for integrations.

## Technologies

- Python 3.11+, Flask, Flask-SQLAlchemy, Werkzeug
- SQLite for local development, PostgreSQL via `DATABASE_URL` in production
- Jinja templates, HTML5, CSS3, vanilla JavaScript
- Gunicorn for production serving

## Structure

```text
app/
  __init__.py       application factory and error handlers
  models.py         User and Workout database models
  auth.py           registration, login, logout
  main.py           dashboard and workout form routes
  api.py            REST health and workout endpoints
templates/          responsive Jinja pages
static/css/app.css design system and responsive layout
static/js/app.js    modal and mobile navigation behavior
config.py           environment-backed configuration
run.py              local entry point
```

## Install and run

1. Create and activate a virtual environment: `python -m venv .venv`, then `.venv\\Scripts\\activate` on Windows or `source .venv/bin/activate` on macOS/Linux.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set a strong `SECRET_KEY`.
4. Run `python run.py` and open `http://127.0.0.1:5000`.

The SQLite database is created automatically on first start. Tables are created through SQLAlchemy and user passwords are stored as Werkzeug password hashes. The application uses signed, HTTP-only Flask sessions and ownership filters on every user-specific query.

## API

- `GET /api/health` returns service status.
- `GET /api/workouts` returns the authenticated user's workouts.
- `POST /api/workouts` accepts JSON with `title`, `workout_type`, `duration`, `calories`, and `completed_on`.

API workout routes require the same authenticated session as the web dashboard and return JSON validation errors with HTTP 400/401 status codes.

## Deployment

Set a production `SECRET_KEY`, a PostgreSQL `DATABASE_URL` such as `postgresql+psycopg://user:password@host:5432/pulsetrack`, and `SESSION_COOKIE_SECURE=true`. Run with `gunicorn --bind 0.0.0.0:8000 run:app` behind a TLS-terminating reverse proxy. For schema evolution in a larger deployment, add Flask-Migrate/Alembic before changing production models.