-- =============================================================================
-- HORECA TICKETING SYSTEM — INITIAL SCHEMA
-- Postgres (Supabase). Implements: RBAC, row-level security, MDM golden
-- records (guests/hostels), audit logging, and PMS integration metadata.
-- =============================================================================

create extension if not exists "pgcrypto";
create extension if not exists "pg_trgm"; -- fuzzy text matching for guest dedup

-- -----------------------------------------------------------------------------
-- ENUMS
-- -----------------------------------------------------------------------------
create type user_role as enum ('admin', 'supervisor', 'agent');
create type ticket_channel as enum ('call', 'whatsapp', 'email', 'reception', 'other');
create type ticket_reason as enum (
  'reservation', 'payment', 'check_in', 'access', 'maintenance',
  'request', 'complaint', 'cancellation', 'modification', 'other'
);
create type ticket_priority as enum ('low', 'medium', 'high', 'urgent');
create type ticket_status as enum ('open', 'in_progress', 'resolved', 'closed');
create type pms_sync_status as enum ('not_integrated', 'pending', 'synced', 'error');
create type dedup_review_status as enum ('pending', 'approved', 'rejected');
create type audit_action as enum (
  'ticket_created', 'ticket_updated', 'ticket_resolved', 'ticket_closed',
  'ticket_reassigned', 'guest_merged', 'guest_created', 'guest_updated',
  'user_created', 'user_updated', 'user_deactivated', 'export_performed',
  'hostel_created', 'hostel_updated'
);

-- -----------------------------------------------------------------------------
-- HOSTELS (master data)
-- -----------------------------------------------------------------------------
create table hostels (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  location text,
  contact_email text,
  contact_phone text,
  pms_status pms_sync_status not null default 'not_integrated',
  pms_provider text, -- e.g. 'mews'
  pms_external_id text, -- id of this property in the external PMS
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Per-property PMS credentials, kept in a separate table (never joined into
-- the general `hostels` select) so that the `hostels_select_all` policy —
-- which intentionally lets every authenticated staff member read the hostel
-- directory for dropdowns — can never leak a secret access token. Only
-- admins may read/write this table. In a hardened production deployment,
-- `access_token` should instead be stored via Supabase Vault
-- (`vault.create_secret`) with only a secret reference kept here.
create table hostel_pms_credentials (
  hostel_id uuid primary key references hostels (id) on delete cascade,
  access_token text not null,
  updated_at timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- APP USERS
-- Mirrors auth.users (Supabase Auth) 1:1. Row is created via trigger on signup
-- (see 0003_auth_trigger.sql) or directly by an admin through the API.
-- -----------------------------------------------------------------------------
create table app_users (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null unique,
  full_name text not null,
  role user_role not null default 'agent',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Many-to-many: which hostel(s) an agent/supervisor is assigned to.
-- For supervisors this defines "their region"; for agents, "their hostel(s)".
create table user_hostels (
  user_id uuid not null references app_users (id) on delete cascade,
  hostel_id uuid not null references hostels (id) on delete cascade,
  primary key (user_id, hostel_id)
);

-- -----------------------------------------------------------------------------
-- GUESTS (MDM golden record)
-- -----------------------------------------------------------------------------
create table guests (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  email text,
  phone text,
  total_tickets int not null default 0,
  last_contact_at timestamptz,
  common_reasons ticket_reason[] not null default '{}',
  preferred_channel ticket_channel,
  linked_reservations text[] not null default '{}',
  data_quality_score int not null default 0 check (data_quality_score between 0 and 100),
  -- normalized name used for trigram fuzzy matching during dedup detection
  name_normalized text generated always as (lower(regexp_replace(full_name, '[^a-zA-Z0-9]+', '', 'g'))) stored,
  merged_into uuid references guests (id), -- set when this record was merged away
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_guests_name_trgm on guests using gin (name_normalized gin_trgm_ops);
create index idx_guests_phone on guests (phone);
create index idx_guests_email on guests (email);

-- Candidate duplicate pairs surfaced by the dedup service, awaiting manual
-- admin/supervisor review before any merge happens (per business decision:
-- dedup merges are MANUAL REVIEW ONLY, never automatic).
create table guest_merge_candidates (
  id uuid primary key default gen_random_uuid(),
  guest_id_a uuid not null references guests (id) on delete cascade,
  guest_id_b uuid not null references guests (id) on delete cascade,
  match_score numeric(5, 2) not null, -- 0-100 confidence score
  match_reason text not null, -- e.g. "name+phone match", "reservation number match"
  status dedup_review_status not null default 'pending',
  reviewed_by uuid references app_users (id),
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (guest_id_a, guest_id_b)
);

-- -----------------------------------------------------------------------------
-- TICKETS
-- -----------------------------------------------------------------------------
create table tickets (
  id uuid primary key default gen_random_uuid(),
  reservation_number text,
  guest_name text not null,
  guest_id uuid references guests (id), -- linked golden record, set by MDM ingestion
  hostel_id uuid not null references hostels (id),
  channel ticket_channel not null,
  reason ticket_reason not null,
  priority ticket_priority not null default 'medium',
  description text not null check (char_length(description) <= 500),
  status ticket_status not null default 'open',
  assignee_id uuid not null references app_users (id),
  created_by uuid not null references app_users (id),
  resolution_notes text,
  recontacted boolean not null default false,
  recontacted_notes text,
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  updated_at timestamptz not null default now()
);

create index idx_tickets_hostel on tickets (hostel_id);
create index idx_tickets_assignee on tickets (assignee_id);
create index idx_tickets_status on tickets (status);
create index idx_tickets_guest on tickets (guest_id);
create index idx_tickets_created_at on tickets (created_at);
create index idx_tickets_reservation_trgm on tickets using gin (reservation_number gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- AUDIT LOG — every create/modify/close/export/merge action, immutable.
-- -----------------------------------------------------------------------------
create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references app_users (id),
  action audit_action not null,
  entity_type text not null, -- 'ticket' | 'guest' | 'user' | 'export'
  entity_id uuid,
  changes jsonb, -- {"field": {"old": ..., "new": ...}} or export params
  created_at timestamptz not null default now()
);

create index idx_audit_entity on audit_logs (entity_type, entity_id);
create index idx_audit_actor on audit_logs (actor_id);
create index idx_audit_created_at on audit_logs (created_at);

-- Ticket-specific change history, human-readable, shown on the ticket detail
-- page's "Change History" panel.
create table ticket_history (
  id uuid primary key default gen_random_uuid(),
  ticket_id uuid not null references tickets (id) on delete cascade,
  changed_by uuid references app_users (id),
  field_name text not null,
  old_value text,
  new_value text,
  created_at timestamptz not null default now()
);

create index idx_ticket_history_ticket on ticket_history (ticket_id);

-- -----------------------------------------------------------------------------
-- updated_at triggers
-- -----------------------------------------------------------------------------
create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_hostels_updated_at before update on hostels
  for each row execute function set_updated_at();
create trigger trg_app_users_updated_at before update on app_users
  for each row execute function set_updated_at();
create trigger trg_guests_updated_at before update on guests
  for each row execute function set_updated_at();
create trigger trg_tickets_updated_at before update on tickets
  for each row execute function set_updated_at();

-- Auto-set resolved_at when status transitions into 'resolved'.
-- Fires on both INSERT (e.g. seed data already marked resolved) and UPDATE
-- (normal agent workflow transitioning a ticket to resolved).
create or replace function set_ticket_resolved_at() returns trigger as $$
begin
  if new.status = 'resolved' then
    if TG_OP = 'INSERT' or old.status is distinct from 'resolved' then
      if new.resolved_at is null then
        new.resolved_at = now();
      end if;
    end if;
  else
    new.resolved_at = null;
  end if;
  return new;
end;
$$ language plpgsql;

create trigger trg_tickets_resolved_at before insert or update on tickets
  for each row execute function set_ticket_resolved_at();

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================
alter table hostels enable row level security;
alter table hostel_pms_credentials enable row level security;
alter table app_users enable row level security;
alter table user_hostels enable row level security;
alter table guests enable row level security;
alter table guest_merge_candidates enable row level security;
alter table tickets enable row level security;
alter table audit_logs enable row level security;
alter table ticket_history enable row level security;

-- Helper: current caller's app_users row (SECURITY DEFINER to avoid recursive
-- RLS lookups while still being safe — it only ever reads the caller's own row).
create or replace function current_app_user()
returns app_users
language sql
stable
security definer
set search_path = public
as $$
  select * from app_users where id = auth.uid();
$$;

create or replace function current_app_role()
returns user_role
language sql
stable
security definer
set search_path = public
as $$
  select role from app_users where id = auth.uid();
$$;

create or replace function is_assigned_to_hostel(target_hostel uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from user_hostels
    where user_id = auth.uid() and hostel_id = target_hostel
  );
$$;

-- ---- hostels ----
-- Everyone authenticated can read the hostel directory (needed for dropdowns);
-- only admins can write.
create policy hostels_select_all on hostels
  for select using (auth.role() = 'authenticated');
create policy hostels_write_admin on hostels
  for all using (current_app_role() = 'admin') with check (current_app_role() = 'admin');

-- ---- hostel_pms_credentials (secrets — admin only, never bulk-read) ----
create policy hostel_pms_credentials_admin_only on hostel_pms_credentials
  for all using (current_app_role() = 'admin') with check (current_app_role() = 'admin');

-- ---- app_users ----
create policy app_users_select_self_or_privileged on app_users
  for select using (
    id = auth.uid() or current_app_role() in ('admin', 'supervisor')
  );
create policy app_users_write_admin on app_users
  for all using (current_app_role() = 'admin') with check (current_app_role() = 'admin');

-- ---- user_hostels ----
create policy user_hostels_select on user_hostels
  for select using (
    user_id = auth.uid() or current_app_role() in ('admin', 'supervisor')
  );
create policy user_hostels_write_admin on user_hostels
  for all using (current_app_role() = 'admin') with check (current_app_role() = 'admin');

-- ---- guests (golden records) ----
-- Least privilege: agents only see guests linked to tickets at their assigned
-- hostels. Supervisors see guests within their region (their hostels).
-- Admins see everything. Writes (merges/edits) restricted to admin/supervisor.
create policy guests_select on guests
  for select using (
    current_app_role() = 'admin'
    or exists (
      select 1 from tickets t
      where t.guest_id = guests.id
        and is_assigned_to_hostel(t.hostel_id)
    )
  );
create policy guests_write_admin_supervisor on guests
  for all using (current_app_role() in ('admin', 'supervisor'))
  with check (current_app_role() in ('admin', 'supervisor'));

create policy dedup_candidates_select on guest_merge_candidates
  for select using (current_app_role() in ('admin', 'supervisor'));
create policy dedup_candidates_write on guest_merge_candidates
  for all using (current_app_role() in ('admin', 'supervisor'))
  with check (current_app_role() in ('admin', 'supervisor'));

-- ---- tickets ----
-- Agent: only tickets at hostels they're assigned to.
-- Supervisor: only tickets at hostels in their region (their assigned hostels).
-- Admin: all tickets.
create policy tickets_select on tickets
  for select using (
    current_app_role() = 'admin'
    or is_assigned_to_hostel(hostel_id)
  );

-- Agents may create tickets only for their own assigned hostels, and only
-- assigned to themselves initially (backend still enforces assignee default).
create policy tickets_insert on tickets
  for insert with check (
    current_app_role() = 'admin'
    or is_assigned_to_hostel(hostel_id)
  );

-- Agents may update tickets at their hostel (status/resolution/recontact) but
-- NOT reassign to someone else — that's enforced at the application layer
-- since RLS can't easily diff old vs new assignee without a trigger; the
-- API layer double-checks role before allowing an `assignee_id` change.
create policy tickets_update on tickets
  for update using (
    current_app_role() = 'admin'
    or is_assigned_to_hostel(hostel_id)
  )
  with check (
    current_app_role() = 'admin'
    or is_assigned_to_hostel(hostel_id)
  );

-- ---- audit_logs / ticket_history ----
-- Read-only for privileged roles; inserts happen via the backend service
-- role (bypasses RLS) so agents cannot tamper with their own audit trail.
create policy audit_logs_select on audit_logs
  for select using (current_app_role() in ('admin', 'supervisor'));
create policy ticket_history_select on ticket_history
  for select using (
    current_app_role() in ('admin', 'supervisor')
    or exists (
      select 1 from tickets t
      where t.id = ticket_history.ticket_id and is_assigned_to_hostel(t.hostel_id)
    )
  );
-- No insert/update/delete policies for audit_logs / ticket_history for regular
-- roles — only the backend's service-role key (which bypasses RLS entirely)
-- writes to these tables, guaranteeing the audit trail cannot be edited by
-- end users, including admins, through the client API.
