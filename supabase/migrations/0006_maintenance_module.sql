-- =============================================================================
-- MAINTENANCE MODULE
--
-- A fully separate system from the guest-facing ticketing module: its own
-- tables, enums, RLS policies, and (in the backend) its own API router and
-- frontend nav section. It shares only what's structurally identical across
-- both domains — the `hostels` and `app_users` tables, and the same
-- `set_updated_at()` trigger helper.
--
-- Access model:
--   - admin: full access to all maintenance tickets, all hostels.
--   - supervisor: VIEW ONLY, scoped to their assigned hostels.
--   - maintenance role: create/view/update, scoped to their assigned hostels.
--   - agent: no access at all (this is intentionally not part of their job).
-- =============================================================================

create type maintenance_status as enum ('open', 'in_progress', 'resolved', 'closed');
create type maintenance_priority as enum ('low', 'medium', 'high', 'urgent');

create table maintenance_tickets (
  id uuid primary key default gen_random_uuid(),
  hostel_id uuid not null references hostels (id),
  title text not null check (char_length(title) <= 200),
  description text not null check (char_length(description) <= 2000),
  status maintenance_status not null default 'open',
  priority maintenance_priority not null default 'medium',
  created_by uuid not null references app_users (id),
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  updated_at timestamptz not null default now()
);

create index idx_maintenance_tickets_hostel on maintenance_tickets (hostel_id);
create index idx_maintenance_tickets_status on maintenance_tickets (status);
create index idx_maintenance_tickets_created_at on maintenance_tickets (created_at);

create trigger trg_maintenance_tickets_updated_at before update on maintenance_tickets
  for each row execute function set_updated_at();

-- Reuses the same "auto-set resolved_at" pattern as guest tickets.
create or replace function set_maintenance_resolved_at() returns trigger as $$
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

create trigger trg_maintenance_tickets_resolved_at before insert or update on maintenance_tickets
  for each row execute function set_maintenance_resolved_at();

-- Photos: one row per uploaded image, storage_path points into the private
-- 'maintenance-photos' Supabase Storage bucket. Uploads/reads are always
-- mediated by the backend (service-role client), which re-checks the
-- caller's role/hostel access before touching storage or this table — so no
-- storage.objects RLS policy is required (the service key bypasses it, and
-- nothing else is ever given direct bucket access).
create table maintenance_ticket_photos (
  id uuid primary key default gen_random_uuid(),
  maintenance_ticket_id uuid not null references maintenance_tickets (id) on delete cascade,
  storage_path text not null,
  uploaded_by uuid not null references app_users (id),
  created_at timestamptz not null default now()
);

create index idx_maintenance_photos_ticket on maintenance_ticket_photos (maintenance_ticket_id);

insert into storage.buckets (id, name, public)
values ('maintenance-photos', 'maintenance-photos', false)
on conflict (id) do nothing;

-- -----------------------------------------------------------------------------
-- ROW LEVEL SECURITY
-- -----------------------------------------------------------------------------
alter table maintenance_tickets enable row level security;
alter table maintenance_ticket_photos enable row level security;

create policy maintenance_tickets_select on maintenance_tickets
  for select using (
    current_app_role() = 'admin'
    or (current_app_role() in ('supervisor', 'maintenance') and is_assigned_to_hostel(hostel_id))
  );

create policy maintenance_tickets_insert on maintenance_tickets
  for insert with check (
    current_app_role() = 'admin'
    or (current_app_role() = 'maintenance' and is_assigned_to_hostel(hostel_id))
  );

create policy maintenance_tickets_update on maintenance_tickets
  for update using (
    current_app_role() = 'admin'
    or (current_app_role() = 'maintenance' and is_assigned_to_hostel(hostel_id))
  )
  with check (
    current_app_role() = 'admin'
    or (current_app_role() = 'maintenance' and is_assigned_to_hostel(hostel_id))
  );

create policy maintenance_photos_select on maintenance_ticket_photos
  for select using (
    exists (
      select 1 from maintenance_tickets mt
      where mt.id = maintenance_ticket_photos.maintenance_ticket_id
        and (
          current_app_role() = 'admin'
          or (current_app_role() in ('supervisor', 'maintenance') and is_assigned_to_hostel(mt.hostel_id))
        )
    )
  );

create policy maintenance_photos_insert on maintenance_ticket_photos
  for insert with check (
    exists (
      select 1 from maintenance_tickets mt
      where mt.id = maintenance_ticket_photos.maintenance_ticket_id
        and (
          current_app_role() = 'admin'
          or (current_app_role() = 'maintenance' and is_assigned_to_hostel(mt.hostel_id))
        )
    )
  );
