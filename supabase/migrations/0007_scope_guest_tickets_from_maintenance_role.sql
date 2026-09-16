-- =============================================================================
-- Isolate the new 'maintenance' role from the guest-ticket/guest-MDM system.
--
-- The original policies on `tickets`, `guests`, and `ticket_history` grant
-- hostel-scoped access to ANY user assigned to that hostel via
-- `user_hostels`, regardless of role — that was fine when the only
-- hostel-assigned roles were 'agent' and 'supervisor'. Now that a
-- maintenance-role user (Robin M) also needs `user_hostels` rows (so the
-- Maintenance module can scope *their* tickets to the same hostels), those
-- same rows would incidentally grant him guest-ticket access too, unless
-- these policies are tightened to check the role explicitly. This migration
-- does that — behavior for 'agent'/'supervisor'/'admin' is unchanged.
-- =============================================================================

drop policy tickets_select on tickets;
create policy tickets_select on tickets
  for select using (
    current_app_role() = 'admin'
    or (current_app_role() in ('agent', 'supervisor') and is_assigned_to_hostel(hostel_id))
  );

drop policy tickets_insert on tickets;
create policy tickets_insert on tickets
  for insert with check (
    current_app_role() = 'admin'
    or (current_app_role() in ('agent', 'supervisor') and is_assigned_to_hostel(hostel_id))
  );

drop policy tickets_update on tickets;
create policy tickets_update on tickets
  for update using (
    current_app_role() = 'admin'
    or (current_app_role() in ('agent', 'supervisor') and is_assigned_to_hostel(hostel_id))
  )
  with check (
    current_app_role() = 'admin'
    or (current_app_role() in ('agent', 'supervisor') and is_assigned_to_hostel(hostel_id))
  );

drop policy guests_select on guests;
create policy guests_select on guests
  for select using (
    current_app_role() = 'admin'
    or exists (
      select 1 from tickets t
      where t.guest_id = guests.id
        and current_app_role() in ('agent', 'supervisor')
        and is_assigned_to_hostel(t.hostel_id)
    )
  );

drop policy ticket_history_select on ticket_history;
create policy ticket_history_select on ticket_history
  for select using (
    current_app_role() in ('admin', 'supervisor')
    or exists (
      select 1 from tickets t
      where t.id = ticket_history.ticket_id
        and current_app_role() = 'agent'
        and is_assigned_to_hostel(t.hostel_id)
    )
  );
