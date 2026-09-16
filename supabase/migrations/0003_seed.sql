-- =============================================================================
-- SEED DATA — 5 hostels, 10 users (1 admin, 2 supervisors, 7 agents),
-- 50 realistic tickets, derived guest golden records, and a couple of
-- deliberate near-duplicate guests to populate the dedup review queue.
--
-- DEV/DEMO ONLY. All seed users share the password below (bcrypt-hashed via
-- pgcrypto, the same algorithm Supabase Auth/GoTrue uses) — rotate or delete
-- these accounts before going to production.
--   Password for every seeded user: HostelDemo#2026
-- =============================================================================

-- -----------------------------------------------------------------------------
-- HOSTELS
-- -----------------------------------------------------------------------------
insert into hostels (name, location, contact_email, contact_phone, pms_status, pms_provider, pms_external_id) values
  ('Sunset Hostel Barcelona',       'Barcelona, Spain',       'frontdesk@sunsetbcn.example',   '+34-93-555-0101', 'synced',         'mews', 'MEWS-BCN-001'),
  ('Backpackers Lisbon',            'Lisbon, Portugal',       'hello@backpackerslis.example',  '+351-21-555-0102', 'synced',         'mews', 'MEWS-LIS-002'),
  ('Old Town Hostel Prague',        'Prague, Czechia',        'info@oldtownprague.example',    '+420-2-5550-0103', 'pending',        'mews', 'MEWS-PRG-003'),
  ('Beach Hostel Lagos',            'Lagos, Portugal',        'stay@beachlagos.example',       '+351-28-255-0104', 'not_integrated', null,   null),
  ('Mountain View Hostel Interlaken','Interlaken, Switzerland','welcome@mviewhostel.example',   '+41-33-555-0105', 'error',          'mews', 'MEWS-INT-005');

-- -----------------------------------------------------------------------------
-- USERS (auth.users + app_users via trigger)
-- Inserting directly into auth.users mirrors what Supabase's GoTrue service
-- does; raw_user_meta_data drives the handle_new_auth_user() trigger from
-- migration 0002, which materializes the app_users profile automatically.
-- -----------------------------------------------------------------------------
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
  confirmation_token, recovery_token, email_change, email_change_token_new
)
select
  '00000000-0000-0000-0000-000000000000',
  u.id, 'authenticated', 'authenticated', u.email,
  crypt('HostelDemo#2026', gen_salt('bf')),
  now(),
  '{"provider":"email","providers":["email"]}',
  jsonb_build_object('full_name', u.full_name, 'role', u.role),
  now(), now(), '', '', '', ''
from (values
  ('11111111-0000-0000-0000-000000000001'::uuid, 'admin@hostelops.example',            'Elena Petrova',  'admin'),
  ('11111111-0000-0000-0000-000000000002'::uuid, 'supervisor.west@hostelops.example',  'Carlos Mendes',  'supervisor'),
  ('11111111-0000-0000-0000-000000000003'::uuid, 'supervisor.east@hostelops.example',  'Jana Novakova',  'supervisor'),
  ('11111111-0000-0000-0000-000000000004'::uuid, 'agent.barcelona1@hostelops.example', 'Marta Duran',    'agent'),
  ('11111111-0000-0000-0000-000000000005'::uuid, 'agent.barcelona2@hostelops.example', 'Pablo Ibarra',   'agent'),
  ('11111111-0000-0000-0000-000000000006'::uuid, 'agent.lisbon1@hostelops.example',    'Rita Alves',     'agent'),
  ('11111111-0000-0000-0000-000000000007'::uuid, 'agent.lagos1@hostelops.example',     'Tiago Sousa',    'agent'),
  ('11111111-0000-0000-0000-000000000008'::uuid, 'agent.prague1@hostelops.example',    'Petra Svobodova','agent'),
  ('11111111-0000-0000-0000-000000000009'::uuid, 'agent.interlaken1@hostelops.example','Lukas Meier',    'agent'),
  ('11111111-0000-0000-0000-000000000010'::uuid, 'agent.multi@hostelops.example',      'Sofia Rossi',    'agent')
) as u(id, email, full_name, role);

-- -----------------------------------------------------------------------------
-- USER <-> HOSTEL ASSIGNMENTS
-- -----------------------------------------------------------------------------
insert into user_hostels (user_id, hostel_id)
select u.user_id, h.id from
  (values
    ('11111111-0000-0000-0000-000000000002'::uuid, 'Sunset Hostel Barcelona'),
    ('11111111-0000-0000-0000-000000000002'::uuid, 'Backpackers Lisbon'),
    ('11111111-0000-0000-0000-000000000002'::uuid, 'Beach Hostel Lagos'),
    ('11111111-0000-0000-0000-000000000003'::uuid, 'Old Town Hostel Prague'),
    ('11111111-0000-0000-0000-000000000003'::uuid, 'Mountain View Hostel Interlaken'),
    ('11111111-0000-0000-0000-000000000004'::uuid, 'Sunset Hostel Barcelona'),
    ('11111111-0000-0000-0000-000000000005'::uuid, 'Sunset Hostel Barcelona'),
    ('11111111-0000-0000-0000-000000000006'::uuid, 'Backpackers Lisbon'),
    ('11111111-0000-0000-0000-000000000007'::uuid, 'Beach Hostel Lagos'),
    ('11111111-0000-0000-0000-000000000008'::uuid, 'Old Town Hostel Prague'),
    ('11111111-0000-0000-0000-000000000009'::uuid, 'Mountain View Hostel Interlaken'),
    ('11111111-0000-0000-0000-000000000010'::uuid, 'Sunset Hostel Barcelona'),
    ('11111111-0000-0000-0000-000000000010'::uuid, 'Backpackers Lisbon')
  ) as u(user_id, hostel_name)
  join hostels h on h.name = u.hostel_name;

-- -----------------------------------------------------------------------------
-- TICKETS (50 rows) — realistic international guest names/scenarios.
-- Resolved timestamps are computed relative to created_at so trend/resolution
-- dashboards have meaningful data out of the box.
-- -----------------------------------------------------------------------------
with raw_tickets (n, guest_name, reservation_number, hostel_name, channel, reason, priority,
                   description, status, agent_email, days_ago, resolve_after_hours,
                   resolution_notes, recontacted, recontacted_notes) as (
  values
  (1,  'Lucas Fernandez',   'RES-2026-0001', 'Sunset Hostel Barcelona', 'call',      'check_in',     'medium', 'Guest arriving 3 hours before official check-in, asked if early check-in is possible.', 'resolved', 'agent.barcelona1@hostelops.example', 58, 1,  'Room was ready early, guest checked in without issue.', false, null),
  (2,  'Emma Thompson',     'RES-2026-0002', 'Sunset Hostel Barcelona', 'whatsapp',  'reservation',  'low',    'Asking to confirm dorm bed reservation for 4 nights.', 'resolved', 'agent.barcelona2@hostelops.example', 57, 2,  'Confirmed reservation details via WhatsApp.', false, null),
  (3,  'Yuki Tanaka',       'RES-2026-0003', 'Sunset Hostel Barcelona', 'email',     'payment',      'high',   'Card was charged twice for the same booking, requesting refund.', 'resolved', 'agent.barcelona1@hostelops.example', 56, 20, 'Duplicate charge confirmed and refunded, guest notified.', true, 'Guest called again 2 days later asking if refund had posted.'),
  (4,  'Liam OConnor',      'RES-2026-0004', 'Sunset Hostel Barcelona', 'reception', 'access',       'medium', 'Key card stopped working after pool visit.', 'resolved', 'agent.multi@hostelops.example', 55, 1,  'Recut key card at reception.', false, null),
  (5,  'Giulia Romano',       'RES-2026-0005', 'Backpackers Lisbon',      'reception', 'maintenance',  'high',   'Air conditioning in room 12 not cooling.', 'resolved', 'agent.lisbon1@hostelops.example', 54, 6,  'Maintenance reset the unit, cooling restored.', false, null),
  (6,  'Mohammed Al-Farsi', 'RES-2026-0006', 'Backpackers Lisbon',      'whatsapp',  'request',      'low',    'Requesting extra towels and a late checkout.', 'resolved', 'agent.lisbon1@hostelops.example', 53, 1,  'Extra towels delivered, late checkout granted until 13:00.', false, null),
  (7,  'Anna Kowalska',     'RES-2026-0007', 'Backpackers Lisbon',      'call',      'complaint',    'urgent', 'Noise complaint from adjacent dorm room overnight.', 'resolved', 'agent.multi@hostelops.example', 52, 3,  'Moved guest to a quieter room, spoke with noisy group.', true, 'Same guest reported noise again the following night.'),
  (8,  'Noah Andersson',    'RES-2026-0008', 'Backpackers Lisbon',      'email',     'cancellation', 'medium', 'Wants to cancel due to flight change, asking about refund policy.', 'resolved', 'agent.lisbon1@hostelops.example', 51, 24, 'Cancellation processed per policy, partial refund issued.', false, null),
  (9,  'Chloe Martin',      'RES-2026-0009', 'Beach Hostel Lagos',      'reception', 'check_in',     'low',    'Passport did not match booking name spelling.', 'resolved', 'agent.lagos1@hostelops.example', 50, 1,  'Corrected spelling in booking, checked in normally.', false, null),
  (10, 'Diego Herrera',     'RES-2026-0010', 'Beach Hostel Lagos',      'call',      'modification', 'medium', 'Wants to extend stay by two extra nights.', 'resolved', 'agent.lagos1@hostelops.example', 49, 4,  'Extension confirmed, availability checked with PMS.', false, null),
  (11, 'Isabella Conti',    'RES-2026-0011', 'Beach Hostel Lagos',      'whatsapp',  'payment',      'high',   'Deposit payment failed but booking shows as unpaid.', 'resolved', 'agent.lagos1@hostelops.example', 48, 5,  'Payment link resent, guest completed payment successfully.', false, null),
  (12, 'Katarina Nemcova',   'RES-2026-0012', 'Old Town Hostel Prague',  'reception', 'access',       'medium', 'Locked out of room, key card demagnetized.', 'resolved', 'agent.prague1@hostelops.example', 47, 1,  'Reissued key card at front desk.', false, null),
  (13, 'Tomas Dvorak',      'RES-2026-0013', 'Old Town Hostel Prague',  'call',      'reservation',  'low',    'Group booking of 6 people, confirming bed layout.', 'resolved', 'agent.prague1@hostelops.example', 46, 2,  'Bed layout confirmed and emailed to group organizer.', false, null),
  (14, 'Stefan Brunner',       'RES-2026-0014', 'Mountain View Hostel Interlaken', 'email', 'maintenance', 'urgent', 'No hot water reported in the entire dorm wing.', 'resolved', 'agent.interlaken1@hostelops.example', 45, 8, 'Boiler issue fixed by on-call technician same day.', false, null),
  (15, 'Hana Kobayashi',    'RES-2026-0015', 'Mountain View Hostel Interlaken', 'reception', 'request', 'low', 'Asking for hiking trail recommendations and a packed lunch.', 'resolved', 'agent.interlaken1@hostelops.example', 44, 1, 'Provided trail map and coordinated packed lunch with kitchen.', false, null),
  (16, 'Isabel Navarro',       'RES-2026-0016', 'Sunset Hostel Barcelona', 'call',      'complaint',    'high',   'Guest unhappy about cleanliness of shared bathroom.', 'resolved', 'agent.barcelona1@hostelops.example', 43, 3, 'Bathroom deep-cleaned, guest offered complimentary drink.', false, null),
  (17, 'Andres Molina',      'RES-2026-0017', 'Sunset Hostel Barcelona', 'whatsapp',  'other',        'low',    'Asking about luggage storage after checkout.', 'in_progress', 'agent.barcelona2@hostelops.example', 6, null, null, false, null),
  (18, 'Ana Silva',         'RES-2026-0018', 'Backpackers Lisbon',      'reception', 'check_in',     'medium', 'Early arrival, no rooms ready yet, requesting storage.', 'resolved', 'agent.lisbon1@hostelops.example', 42, 2, 'Luggage stored, guest checked in at 15:00 as scheduled.', false, null),
  (19, 'Ana  Silva',        'RES-2026-0044', 'Backpackers Lisbon',      'email',     'payment',      'medium', 'Asking for an invoice copy for reimbursement purposes.', 'resolved', 'agent.lisbon1@hostelops.example', 12, 3, 'Invoice PDF emailed to guest.', false, null),
  (20, 'Helena Duarte',        'RES-2026-0019', 'Backpackers Lisbon',      'call',      'cancellation', 'medium', 'Cancelling due to illness, has travel insurance.', 'resolved', 'agent.lisbon1@hostelops.example', 41, 2, 'Cancellation confirmed, insurance documentation provided.', false, null),
  (21, 'Bruno Martins',       'RES-2026-0020', 'Beach Hostel Lagos',      'whatsapp',  'modification', 'low',    'Wants to switch from dorm bed to private room.', 'resolved', 'agent.lagos1@hostelops.example', 40, 2, 'Upgraded to private room, price difference charged.', false, null),
  (22, 'Camille Dubois',    'RES-2026-0021', 'Beach Hostel Lagos',      'reception', 'access',       'medium', 'Beach locker key lost.', 'resolved', 'agent.lagos1@hostelops.example', 39, 1, 'Replacement lock issued, small fee applied.', false, null),
  (23, 'Marco Bianchi',     'RES-2026-0022', 'Old Town Hostel Prague',  'call',      'complaint',    'urgent', 'Reports bed bugs in dorm room, very upset.', 'resolved', 'agent.prague1@hostelops.example', 38, 10, 'Room inspected, pest control called, guest relocated to another hostel wing.', true, 'Guest raised the same concern again after moving rooms.'),
  (24, 'Grace Okafor',      'RES-2026-0023', 'Old Town Hostel Prague',  'email',     'reservation',  'low',    'Confirming breakfast is included in the rate.', 'resolved', 'agent.prague1@hostelops.example', 37, 1, 'Confirmed breakfast inclusion via email.', false, null),
  (25, 'Sven Johansson',    'RES-2026-0024', 'Mountain View Hostel Interlaken', 'reception', 'maintenance', 'medium', 'Window in room 5 does not close properly.', 'resolved', 'agent.interlaken1@hostelops.example', 36, 6, 'Window latch repaired by maintenance.', false, null),
  (26, 'Fatima Zahra',      'RES-2026-0025', 'Mountain View Hostel Interlaken', 'whatsapp', 'request', 'low', 'Asking about laundry service availability.', 'resolved', 'agent.interlaken1@hostelops.example', 35, 1, 'Explained self-service laundry hours and pricing.', false, null),
  (27, 'Lucas Fernandez',   'RES-2026-0026', 'Sunset Hostel Barcelona', 'call',      'modification', 'medium', 'Returning guest wants to add 2 more nights to current stay.', 'resolved', 'agent.barcelona1@hostelops.example', 34, 3, 'Extension confirmed, room availability checked.', false, null),
  (28, 'Noor Abbas',        'RES-2026-0027', 'Sunset Hostel Barcelona', 'reception', 'check_in',     'low',    'Guest arrived without printed confirmation.', 'resolved', 'agent.barcelona2@hostelops.example', 33, 1, 'Located booking by email, checked in normally.', false, null),
  (29, 'Ingrid Larsen',     'RES-2026-0028', 'Backpackers Lisbon',      'email',     'cancellation', 'high',   'Requesting full refund citing hostel closed pool unexpectedly.', 'in_progress', 'agent.lisbon1@hostelops.example', 9, null, null, false, null),
  (30, 'Julien Moreau',     'RES-2026-0029', 'Backpackers Lisbon',      'whatsapp',  'other',        'low',    'Asking for nearby pharmacy recommendations.', 'resolved', 'agent.multi@hostelops.example', 32, 1, 'Sent list of nearby pharmacies and opening hours.', false, null),
  (31, 'Wei Zhang',         'RES-2026-0030', 'Beach Hostel Lagos',      'call',      'payment',      'medium', 'Currency conversion looks incorrect on the invoice.', 'resolved', 'agent.lagos1@hostelops.example', 31, 4, 'Recalculated invoice with correct exchange rate, corrected copy sent.', false, null),
  (32, 'Beatriz Costa',     'RES-2026-0031', 'Beach Hostel Lagos',      'reception', 'access',       'low',    'Cannot get WiFi to connect in the room.', 'resolved', 'agent.lagos1@hostelops.example', 30, 1, 'Reset router, provided correct WiFi password.', false, null),
  (33, 'Henrik Nilsson',    'RES-2026-0032', 'Old Town Hostel Prague',  'whatsapp',  'reservation',  'medium', 'Wants to confirm if pets are allowed for upcoming stay.', 'resolved', 'agent.prague1@hostelops.example', 29, 2, 'Informed guest pets are not allowed per hostel policy.', false, null),
  (34, 'Zainab Hussain',    'RES-2026-0033', 'Old Town Hostel Prague',  'call',      'complaint',    'medium', 'Reception staff was rude during check-in.', 'resolved', 'agent.prague1@hostelops.example', 28, 12, 'Apologized to guest, feedback logged for staff coaching.', false, null),
  (35, 'Oliver Schmidt',    'RES-2026-0034', 'Mountain View Hostel Interlaken', 'email', 'modification', 'low', 'Wants to change arrival date by one day.', 'resolved', 'agent.interlaken1@hostelops.example', 27, 3, 'Date changed in system, confirmation email sent.', false, null),
  (36, 'Priya Sharma',      'RES-2026-0035', 'Mountain View Hostel Interlaken', 'reception', 'maintenance', 'high', 'Shower drain clogged in shared bathroom.', 'resolved', 'agent.interlaken1@hostelops.example', 26, 5, 'Plumber cleared the drain same day.', false, null),
  (37, 'Giulia Romano',       'RES-2026-0036', 'Backpackers Lisbon',      'call',      'request',      'low',    'Asking for a taxi to be booked to the airport.', 'resolved', 'agent.multi@hostelops.example', 25, 1, 'Taxi booked for requested time.', false, null),
  (38, 'Ahmed Hassan',      'RES-2026-0037', 'Sunset Hostel Barcelona', 'whatsapp',  'payment',      'urgent', 'Booking site shows paid, hostel PMS shows unpaid.', 'resolved', 'agent.barcelona1@hostelops.example', 24, 6, 'Confirmed with booking channel, payment matched manually in PMS.', false, null),
  (39, 'Laura Jimenez',     'RES-2026-0038', 'Sunset Hostel Barcelona', 'reception', 'check_in',     'medium', 'Guest is a minor traveling with an ID document question.', 'resolved', 'agent.barcelona2@hostelops.example', 23, 2, 'Verified guardian consent form, checked in per policy.', false, null),
  (40, 'Viktor Petrov',     'RES-2026-0039', 'Beach Hostel Lagos',      'email',     'cancellation', 'low',    'No-show due to missed flight connection, asking about policy.', 'closed', 'agent.lagos1@hostelops.example', 22, 20, 'No-show fee applied per policy, case closed.', false, null),
  (41, 'Meera Nair',        'RES-2026-0040', 'Beach Hostel Lagos',      'call',      'other',        'low',    'Asking if the hostel organizes surf lessons.', 'resolved', 'agent.lagos1@hostelops.example', 21, 1, 'Shared partner surf school contact info.', false, null),
  (42, 'Karim Benali',      'RES-2026-0041', 'Old Town Hostel Prague',  'whatsapp',  'access',       'medium', 'Front door code is not working at night entrance.', 'resolved', 'agent.prague1@hostelops.example', 20, 2, 'Updated door code and re-sent to all current guests.', false, null),
  (43, 'Olga Ivanova',      'RES-2026-0042', 'Old Town Hostel Prague',  'reception', 'complaint',    'high',   'Overbooked dorm, guest has no assigned bed.', 'resolved', 'agent.prague1@hostelops.example', 19, 4, 'Relocated guest to upgraded room at no extra charge.', false, null),
  (44, 'Daniel Kim',        'RES-2026-0043', 'Mountain View Hostel Interlaken', 'email', 'reservation', 'low', 'Confirming cancellation policy before booking a group trip.', 'resolved', 'agent.interlaken1@hostelops.example', 18, 1, 'Cancellation policy explained in detail via email.', false, null),
  (45, 'Amara Nwosu',       'RES-2026-0045', 'Mountain View Hostel Interlaken', 'call', 'modification', 'medium', 'Wants to add one more guest to existing private room booking.', 'open', 'agent.interlaken1@hostelops.example', 4, null, null, false, null),
  (46, 'Yusuf Demir',       'RES-2026-0046', 'Sunset Hostel Barcelona', 'reception', 'access',       'low',    'Safe box code forgotten, needs reset.', 'open', 'agent.multi@hostelops.example', 3, null, null, false, null),
  (47, 'Ines Ferreira',     'RES-2026-0047', 'Backpackers Lisbon',      'whatsapp',  'request',      'medium', 'Requesting a late checkout for a flight at midnight.', 'open', 'agent.lisbon1@hostelops.example', 2, null, null, false, null),
  (48, 'Fernando Castro',     'RES-2026-0048', 'Beach Hostel Lagos',      'call',      'payment',      'high',   'Refund promised last week has not appeared in guest account.', 'in_progress', 'agent.lagos1@hostelops.example', 5, null, null, false, null),
  (49, 'Eva Kralova',     'RES-2026-0049', 'Old Town Hostel Prague',  'email',     'complaint',    'urgent', 'Guest reporting theft from locker, requesting police report assistance.', 'open', 'agent.prague1@hostelops.example', 1, null, null, false, null),
  (50, 'Elif Yildiz',       'RES-2026-0050', 'Mountain View Hostel Interlaken', 'reception', 'check_in', 'low', 'Wheelchair accessibility question before arrival.', 'open', 'agent.interlaken1@hostelops.example', 0, null, null, false, null)
)
insert into tickets (
  reservation_number, guest_name, hostel_id, channel, reason, priority, description,
  status, assignee_id, created_by, resolution_notes, recontacted, recontacted_notes,
  created_at, resolved_at
)
select
  rt.reservation_number, rt.guest_name, h.id, rt.channel::ticket_channel, rt.reason::ticket_reason,
  rt.priority::ticket_priority, rt.description, rt.status::ticket_status, au.id, au.id,
  rt.resolution_notes, rt.recontacted, rt.recontacted_notes,
  now() - (rt.days_ago || ' days')::interval,
  case when rt.resolve_after_hours is not null
    then now() - (rt.days_ago || ' days')::interval + (rt.resolve_after_hours || ' hours')::interval
    else null
  end
from raw_tickets rt
join hostels h on h.name = rt.hostel_name
join app_users au on au.email = rt.agent_email;

-- -----------------------------------------------------------------------------
-- GUESTS (golden records) — one per distinct guest name appearing in tickets,
-- with fields aggregated from their linked tickets.
-- -----------------------------------------------------------------------------
insert into guests (full_name, total_tickets, last_contact_at, common_reasons, preferred_channel, linked_reservations, data_quality_score, email, phone)
select
  t.guest_name,
  count(*),
  max(t.created_at),
  array_agg(distinct t.reason),
  (array_agg(t.channel order by t.created_at desc))[1],
  array_agg(distinct t.reservation_number),
  -- simple completeness score: has a reservation number (+50), appears more
  -- than once i.e. richer history (+30), name has both first+last (+20)
  least(100,
    (case when count(distinct t.reservation_number) > 0 then 50 else 0 end) +
    (case when count(*) > 1 then 30 else 0 end) +
    (case when t.guest_name like '% %' then 20 else 0 end)
  ),
  null, -- email not captured at seed time (channel was not email for most)
  null  -- phone not captured at seed time
from tickets t
group by t.guest_name;

update tickets t
set guest_id = g.id
from guests g
where g.full_name = t.guest_name;

-- -----------------------------------------------------------------------------
-- DEDUP REVIEW QUEUE — deliberate near-duplicate ("Ana Silva" vs "Ana  Silva"
-- with an extra space, ticket #18 vs #19) surfaced for manual admin review.
-- -----------------------------------------------------------------------------
insert into guest_merge_candidates (guest_id_a, guest_id_b, match_score, match_reason, status)
select g1.id, g2.id, 92.50, 'Name match (normalized) + same hostel + overlapping reason (payment/check-in)', 'pending'
from guests g1, guests g2
where g1.full_name = 'Ana Silva' and g2.full_name = 'Ana  Silva';

-- -----------------------------------------------------------------------------
-- TICKET HISTORY — minimal illustrative entries for resolved tickets so the
-- "Change History" panel has content out of the box.
-- -----------------------------------------------------------------------------
insert into ticket_history (ticket_id, changed_by, field_name, old_value, new_value, created_at)
select t.id, t.assignee_id, 'status', 'open', 'resolved', t.resolved_at
from tickets t
where t.status in ('resolved', 'closed') and t.resolved_at is not null;

insert into ticket_history (ticket_id, changed_by, field_name, old_value, new_value, created_at)
select t.id, t.assignee_id, 'status', 'open', 'in_progress', t.created_at + interval '1 hour'
from tickets t
where t.status = 'in_progress';
