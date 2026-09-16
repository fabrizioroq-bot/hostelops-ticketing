-- =============================================================================
-- Sync auth.users -> app_users automatically.
-- When the backend creates a user via the Supabase Admin API
-- (auth.admin.createUser), it passes role/full_name/hostel_ids in
-- `raw_user_meta_data`. This trigger materializes the app_users row so the
-- profile always exists, even if the API call is interrupted after the
-- auth.users insert.
-- =============================================================================

create or replace function handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into app_users (id, email, full_name, role)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.email),
    coalesce((new.raw_user_meta_data ->> 'role')::user_role, 'agent')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger trg_on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_auth_user();
