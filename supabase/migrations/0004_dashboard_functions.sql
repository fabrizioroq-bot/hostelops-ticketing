-- =============================================================================
-- DASHBOARD AGGREGATION FUNCTIONS
--
-- All functions are STABLE / SECURITY INVOKER (the default) — they run as
-- whichever role calls them via PostgREST, so the same Row Level Security
-- policies that govern `select * from tickets` also govern every aggregate
-- below. A supervisor's dashboard therefore only ever aggregates over the
-- tickets their RLS policy already allows them to see; no separate
-- authorization logic is needed in the backend for these reads.
--
-- Every filter argument is nullable; passing NULL means "no filter on this
-- dimension" via the `p_x is null or column = p_x` pattern.
-- =============================================================================

create or replace function fn_dashboard_overview(
  p_hostel_id uuid default null,
  p_assignee_id uuid default null,
  p_priority ticket_priority default null,
  p_reason ticket_reason default null,
  p_date_from timestamptz default null,
  p_date_to timestamptz default null
) returns jsonb
language sql stable
as $$
  select jsonb_build_object(
    'total', count(*),
    'open', count(*) filter (where status = 'open'),
    'in_progress', count(*) filter (where status = 'in_progress'),
    'resolved', count(*) filter (where status = 'resolved'),
    'closed', count(*) filter (where status = 'closed'),
    'today', count(*) filter (where created_at >= date_trunc('day', now())),
    'this_week', count(*) filter (where created_at >= date_trunc('week', now())),
    'this_month', count(*) filter (where created_at >= date_trunc('month', now()))
  )
  from tickets
  where (p_hostel_id is null or hostel_id = p_hostel_id)
    and (p_assignee_id is null or assignee_id = p_assignee_id)
    and (p_priority is null or priority = p_priority)
    and (p_reason is null or reason = p_reason)
    and (p_date_from is null or created_at >= p_date_from)
    and (p_date_to is null or created_at <= p_date_to);
$$;

create or replace function fn_dashboard_trend(
  p_hostel_id uuid default null,
  p_assignee_id uuid default null,
  p_priority ticket_priority default null,
  p_reason ticket_reason default null,
  p_date_from timestamptz default null,
  p_date_to timestamptz default null
) returns table (day date, created_count bigint, resolved_count bigint)
language sql stable
as $$
  with created as (
    select date_trunc('day', created_at)::date as day, count(*) as created_count
    from tickets
    where (p_hostel_id is null or hostel_id = p_hostel_id)
      and (p_assignee_id is null or assignee_id = p_assignee_id)
      and (p_priority is null or priority = p_priority)
      and (p_reason is null or reason = p_reason)
      and (p_date_from is null or created_at >= p_date_from)
      and (p_date_to is null or created_at <= p_date_to)
    group by 1
  ),
  resolved as (
    select date_trunc('day', resolved_at)::date as day, count(*) as resolved_count
    from tickets
    where resolved_at is not null
      and (p_hostel_id is null or hostel_id = p_hostel_id)
      and (p_assignee_id is null or assignee_id = p_assignee_id)
      and (p_priority is null or priority = p_priority)
      and (p_reason is null or reason = p_reason)
      and (p_date_from is null or resolved_at >= p_date_from)
      and (p_date_to is null or resolved_at <= p_date_to)
    group by 1
  )
  select coalesce(c.day, r.day), coalesce(c.created_count, 0), coalesce(r.resolved_count, 0)
  from created c
  full outer join resolved r on c.day = r.day
  order by 1;
$$;

create or replace function fn_dashboard_by_reason(
  p_hostel_id uuid default null, p_assignee_id uuid default null,
  p_priority ticket_priority default null, p_date_from timestamptz default null, p_date_to timestamptz default null
) returns table (reason ticket_reason, count bigint)
language sql stable
as $$
  select reason, count(*) from tickets
  where (p_hostel_id is null or hostel_id = p_hostel_id)
    and (p_assignee_id is null or assignee_id = p_assignee_id)
    and (p_priority is null or priority = p_priority)
    and (p_date_from is null or created_at >= p_date_from)
    and (p_date_to is null or created_at <= p_date_to)
  group by reason order by 2 desc;
$$;

create or replace function fn_dashboard_by_channel(
  p_hostel_id uuid default null, p_assignee_id uuid default null,
  p_date_from timestamptz default null, p_date_to timestamptz default null
) returns table (channel ticket_channel, count bigint)
language sql stable
as $$
  select channel, count(*) from tickets
  where (p_hostel_id is null or hostel_id = p_hostel_id)
    and (p_assignee_id is null or assignee_id = p_assignee_id)
    and (p_date_from is null or created_at >= p_date_from)
    and (p_date_to is null or created_at <= p_date_to)
  group by channel order by 2 desc;
$$;

create or replace function fn_dashboard_by_priority_status(
  p_hostel_id uuid default null, p_date_from timestamptz default null, p_date_to timestamptz default null
) returns table (priority ticket_priority, status ticket_status, count bigint)
language sql stable
as $$
  select priority, status, count(*) from tickets
  where (p_hostel_id is null or hostel_id = p_hostel_id)
    and (p_date_from is null or created_at >= p_date_from)
    and (p_date_to is null or created_at <= p_date_to)
  group by priority, status order by priority, status;
$$;

-- p_group_by: 'hostel' or 'agent'
create or replace function fn_dashboard_resolution_time(
  p_group_by text default 'hostel', p_date_from timestamptz default null, p_date_to timestamptz default null
) returns table (group_id uuid, group_label text, avg_hours numeric, resolved_count bigint)
language sql stable
as $$
  select
    case when p_group_by = 'agent' then t.assignee_id else t.hostel_id end,
    case when p_group_by = 'agent' then u.full_name else h.name end,
    round(avg(extract(epoch from (t.resolved_at - t.created_at)) / 3600.0)::numeric, 1),
    count(*)
  from tickets t
  join hostels h on h.id = t.hostel_id
  join app_users u on u.id = t.assignee_id
  where t.resolved_at is not null
    and (p_date_from is null or t.created_at >= p_date_from)
    and (p_date_to is null or t.created_at <= p_date_to)
  group by 1, 2
  order by 3 desc;
$$;

create or replace function fn_dashboard_recontact_rate(
  p_hostel_id uuid default null, p_date_from timestamptz default null, p_date_to timestamptz default null
) returns jsonb
language sql stable
as $$
  select jsonb_build_object(
    'total_resolved', count(*) filter (where status in ('resolved', 'closed')),
    'recontacted', count(*) filter (where recontacted = true),
    'rate_pct', case when count(*) filter (where status in ('resolved', 'closed')) = 0 then 0
      else round(100.0 * count(*) filter (where recontacted = true) / count(*) filter (where status in ('resolved', 'closed')), 1)
    end
  )
  from tickets
  where (p_hostel_id is null or hostel_id = p_hostel_id)
    and (p_date_from is null or created_at >= p_date_from)
    and (p_date_to is null or created_at <= p_date_to);
$$;

create or replace function fn_hostel_performance(
  p_date_from timestamptz default null, p_date_to timestamptz default null
) returns table (hostel_id uuid, hostel_name text, ticket_count bigint, avg_resolution_hours numeric)
language sql stable
as $$
  select h.id, h.name, count(t.id),
    round(avg(extract(epoch from (t.resolved_at - t.created_at)) / 3600.0) filter (where t.resolved_at is not null)::numeric, 1)
  from hostels h
  left join tickets t on t.hostel_id = h.id
    and (p_date_from is null or t.created_at >= p_date_from)
    and (p_date_to is null or t.created_at <= p_date_to)
  group by h.id, h.name
  order by 3 desc;
$$;

create or replace function fn_hostel_top_issues(p_hostel_id uuid, p_limit int default 3)
returns table (reason ticket_reason, count bigint)
language sql stable
as $$
  select reason, count(*) from tickets
  where hostel_id = p_hostel_id
  group by reason order by 2 desc limit p_limit;
$$;

create or replace function fn_agent_workload(p_hostel_id uuid default null)
returns table (assignee_id uuid, agent_name text, hostel_id uuid, hostel_name text, ticket_count bigint)
language sql stable
as $$
  select u.id, u.full_name, h.id, h.name, count(t.id)
  from tickets t
  join app_users u on u.id = t.assignee_id
  join hostels h on h.id = t.hostel_id
  where (p_hostel_id is null or t.hostel_id = p_hostel_id)
  group by u.id, u.full_name, h.id, h.name
  order by 5 desc;
$$;

create or replace function fn_agent_performance(p_agent_id uuid)
returns jsonb
language sql stable
as $$
  select jsonb_build_object(
    'open', count(*) filter (where status = 'open'),
    'in_progress', count(*) filter (where status = 'in_progress'),
    'resolved', count(*) filter (where status = 'resolved'),
    'resolved_this_week', count(*) filter (where status = 'resolved' and resolved_at >= date_trunc('week', now())),
    'avg_resolution_hours', round(avg(extract(epoch from (resolved_at - created_at)) / 3600.0)
      filter (where resolved_at is not null)::numeric, 1)
  )
  from tickets where assignee_id = p_agent_id;
$$;

-- ---- Data Quality Dashboard ----
create or replace function fn_data_quality_summary()
returns jsonb
language sql stable
as $$
  select jsonb_build_object(
    'duplicate_candidates_pending', (select count(*) from guest_merge_candidates where status = 'pending'),
    'merged_this_month', (select count(*) from guest_merge_candidates
      where status = 'approved' and reviewed_at >= date_trunc('month', now())),
    'total_tickets', (select count(*) from tickets),
    'incomplete_tickets', (select count(*) from tickets
      where guest_id is null or (status in ('resolved', 'closed') and resolution_notes is null)),
    'completeness_pct', (select case when count(*) = 0 then 100 else round(
        100.0 * count(*) filter (where guest_id is not null
          and (status not in ('resolved', 'closed') or resolution_notes is not null)) / count(*), 1)
      end from tickets),
    'avg_guest_data_quality_score', (select round(avg(data_quality_score)::numeric, 1) from guests where merged_into is null)
  );
$$;

create or replace function fn_incomplete_tickets(p_limit int default 50)
returns table (id uuid, guest_name text, hostel_id uuid, reason ticket_reason, status ticket_status,
               missing_fields text[], created_at timestamptz)
language sql stable
as $$
  select t.id, t.guest_name, t.hostel_id, t.reason, t.status,
    array_remove(array[
      case when t.guest_id is null then 'guest_link' end,
      case when t.status in ('resolved', 'closed') and t.resolution_notes is null then 'resolution_notes' end
    ], null),
    t.created_at
  from tickets t
  where t.guest_id is null or (t.status in ('resolved', 'closed') and t.resolution_notes is null)
  order by t.created_at desc
  limit p_limit;
$$;

-- Dashboards are for authenticated staff only — explicitly deny anonymous
-- callers and grant to authenticated (RLS on the underlying tables still
-- scopes what each authenticated role actually sees).
revoke execute on all functions in schema public from anon;
grant execute on all functions in schema public to authenticated;

