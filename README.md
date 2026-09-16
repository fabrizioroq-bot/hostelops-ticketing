# HostelOps Ticketing

A production-ready internal ticketing system for hostel "front office as a
service" operations: multi-hostel ticket management, guest master data
management (MDM) with golden records and manual-review deduplication,
role-based dashboards, and CSV/Excel exports.

## Stack

- **Frontend:** React + Vite + TypeScript + Mantine UI + Recharts
- **Backend:** Python + FastAPI
- **Database/Auth:** Supabase (PostgreSQL with Row Level Security + Supabase Auth)
- **PMS integration:** Mews Connector API (pluggable adapter pattern for others)
- **Scheduled reports:** APScheduler + Resend (weekly PDF summary email)

## Repository layout

```
supabase/migrations/   Database schema, RLS policies, dashboard SQL functions, seed data
backend/                FastAPI app (app/), tests (app/tests/), Dockerfile
frontend/                React app (src/), Dockerfile, nginx.conf
docs/                    Deployment guide and API reference
docker-compose.yml       Alternative VPS deployment (backend + frontend containers)
```

## Quick start

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for full step-by-step
instructions (Supabase project setup, environment variables, running
migrations, deploying to Vercel + Supabase or Docker, creating the first
admin user, and running deduplication). Short version:

```bash
# 1. Create a Supabase project, run supabase/migrations/*.sql in order via the SQL Editor

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase keys
pytest -q               # 11 tests, no live Supabase needed
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
cp .env.example .env    # fill in Supabase URL/anon key + backend URL
npm run dev
```

Seeded login (dev/demo only — **rotate before production**):
`admin@hostelops.example` / `HostelDemo#2026` (also `m.chizzolini@rb-horeca.com`
as a supervisor, `l.regordosa@rb-horeca.com` as a receptionist, `r.m@rb-horeca.com`
as maintenance — full roster in `supabase/migrations/0008_replace_seed_data.sql`).

## Security model

- **Authentication:** Supabase Auth (email/password, bcrypt-hashed
  passwords, JWT sessions). The backend never sees a password — it only
  verifies the resulting JWT (`app/core/security.py`).
- **RBAC:** Admin / Supervisor / Agent, enforced at two independent
  layers:
  1. FastAPI route dependencies (`require_roles(...)`) reject the wrong
     role before any query runs.
  2. **Row Level Security** on every table (`supabase/migrations/0001_init.sql`)
     — even a bug in the backend's own role checks can't leak data across
     hostels or roles, because Postgres itself won't return rows the
     caller isn't allowed to see.
- **Least privilege:** Agents see only tickets/guests tied to their
  assigned hostel(s); supervisors, their region (assigned hostels);
  admins, everything. PMS credentials live in a separate admin-only table
  so they're never returned by the general hostel directory read.
- **Audit log:** Every ticket create/update/resolve/close/reassign, guest
  merge, user change, and export is recorded in `audit_logs`, writable
  only by backend service-role code — not through the regular API, so not
  even an Admin can edit the trail through normal use.
- **Sessions:** 30-minute JWT expiry (set in the Supabase dashboard, see
  deployment guide) plus a frontend inactivity timer
  (`frontend/src/hooks/useInactivityLogout.ts`) that signs the user out
  after 30 minutes of no interaction, and a clean `supabase.auth.signOut()`
  on logout that invalidates the session.
- **HTTPS:** required in production — Vercel and most container platforms
  terminate TLS automatically; see the deployment guide's VPS section for
  the manual case.

## MDM (Master Data Management)

Guests, Hostels, and Users are each a single golden-record domain:

- **Ticket creation** runs `find_or_create_guest()`
  (`backend/app/services/guest_service.py`), which links to an existing
  guest only on an *exact* signal (matching reservation number or exact
  normalized name) — anything fuzzier creates a new record rather than
  guessing.
- **Deduplication is manual-review-only.** A separate scan
  (`backend/app/services/dedup_service.py`) fuzzy-matches all golden
  records and proposes candidates; nothing merges without an
  admin/supervisor approving it in the Deduplication Review page.
- **Data quality** is tracked per guest (0–100 completeness score) and
  surfaced on the Data Quality dashboard, alongside a list of tickets
  missing critical fields.

## Dashboards

Executive (admin/supervisor), Agent (everyone, own performance),
Data Quality (admin), and Hostel Performance (admin/supervisor) — all
backed by SQL aggregation functions
(`supabase/migrations/0004_dashboard_functions.sql`) that run through the
caller's own RLS-scoped connection, so results are automatically bounded
by what that role is allowed to see.

## Maintenance module

A fully separate system from guest ticketing — own table
(`maintenance_tickets`), own role (`maintenance`), own nav section, own
Supabase Storage bucket for repair photos
(`supabase/migrations/0006_maintenance_module.sql`). Admins have full
access; supervisors are view-only, scoped to their hostels; the
`maintenance` role can create/view/update, scoped to their hostels; agents
have no access at all. Photo uploads go through the backend
(`POST /maintenance-tickets/{id}/photos`), which writes to the private
bucket via the service-role key and hands back short-lived signed URLs —
the bucket itself is never public.

## Tests

```bash
cd backend && source .venv/bin/activate && pytest -q
```

11 tests covering the JWT auth dependency (`app/tests/test_auth.py`) and
ticket CRUD business rules — hostel-scoped access, reassignment
permissions, status-transition audit actions
(`app/tests/test_tickets.py`) — using an in-memory fake of the
supabase-py query builder, so no live database is required to run them.

## Further reading

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — full setup and deployment walkthrough
- [docs/API.md](docs/API.md) — endpoint reference (also available live at `/docs` on the running backend)
