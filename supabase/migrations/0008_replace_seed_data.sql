-- =============================================================================
-- REPLACE SEED DATA WITH REAL RB-HORECA ROSTER/PROPERTIES
--
-- Removes the fictional demo hostels and staff (agents/supervisors) and
-- replaces them with the real rb-horeca roster and 4 real hotels. The demo
-- admin account (admin@hostelops.example) is intentionally kept so there's
-- always a way to log in and manage users/hostels.
--
-- Guest traveler names within tickets are left as-is (they were never the
-- "fictional people" being replaced — only staff/hostels were) and each
-- ticket is remapped onto the new real hostel + receptionist that most
-- closely mirrors its original assignment.
--
-- DEV/DEMO ONLY. New seed users share the password below — rotate before
-- production use.
--   Password for every seeded user: HostelDemo#2026
-- =============================================================================

-- -----------------------------------------------------------------------------
-- WIPE OLD DEMO DATA (keep the admin account)
-- Order matters for FK safety: tickets before guests (tickets.guest_id
-- references guests), then auth.users (cascades to app_users ->
-- user_hostels), then hostels (cascades to hostel_pms_credentials).
-- Maintenance tables are new in this deployment so there's nothing to wipe
-- there yet.
-- -----------------------------------------------------------------------------
delete from tickets;
delete from guests;
delete from auth.users where email <> 'admin@hostelops.example';
delete from hostels;

-- -----------------------------------------------------------------------------
-- HOTELS
-- -----------------------------------------------------------------------------
insert into hostels (name, location, contact_email, contact_phone, pms_status) values
  ('Rembrandt Square Hotel', 'Amsterdam, Netherlands', 'frontdesk@rembrandtsquare.rb-horeca.com', '+31-20-555-0111', 'not_integrated'),
  ('Durty Nellys',           'Amsterdam, Netherlands', 'frontdesk@durtynellys.rb-horeca.com',     '+31-20-555-0112', 'not_integrated'),
  ('This Hostel',            'Amsterdam, Netherlands', 'frontdesk@thishostel.rb-horeca.com',      '+31-20-555-0113', 'not_integrated'),
  ('Westlake',               'Amsterdam, Netherlands', 'frontdesk@westlake.rb-horeca.com',        '+31-20-555-0114', 'not_integrated');

-- -----------------------------------------------------------------------------
-- USERS (auth.users + app_users via trigger)
-- 5 supervisors, 2 receptionists (role='agent' — the existing operational
-- role), 1 maintenance-role user (Robin M).
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
  ('22222222-0000-0000-0000-000000000001'::uuid, 'm.chizzolini@rb-horeca.com', 'Mariana Chizzolini', 'supervisor'),
  ('22222222-0000-0000-0000-000000000002'::uuid, 'm.zimmerman@rb-horeca.com',  'Melissa Zimmerman',  'supervisor'),
  ('22222222-0000-0000-0000-000000000003'::uuid, 'm.duvet@rb-horeca.com',      'Maryne Duvet',       'supervisor'),
  ('22222222-0000-0000-0000-000000000004'::uuid, 'm.jouvet@rb-horeca.com',     'Maryne Jouvet',      'supervisor'),
  ('22222222-0000-0000-0000-000000000005'::uuid, 'm.pool@rb-horeca.com',       'Milan Pool',         'supervisor'),
  ('22222222-0000-0000-0000-000000000006'::uuid, 'l.regordosa@rb-horeca.com',  'Leticia Regordosa',  'agent'),
  ('22222222-0000-0000-0000-000000000007'::uuid, 'j.damian@rb-horeca.com',     'Jean Damian',        'agent'),
  ('22222222-0000-0000-0000-000000000008'::uuid, 'r.m@rb-horeca.com',          'Robin M',            'maintenance')
) as u(id, email, full_name, role);

-- -----------------------------------------------------------------------------
-- USER <-> HOSTEL ASSIGNMENTS
-- All 5 supervisors and both receptionists cover all 4 hotels (rb-horeca
-- operates as a single region). Robin M (maintenance) is also assigned to
-- all 4 hotels — required for the Maintenance module's hostel-scoped RLS —
-- but migration 0007 ensures that assignment does NOT grant him any
-- guest-ticket access.
-- -----------------------------------------------------------------------------
insert into user_hostels (user_id, hostel_id)
select u.id, h.id
from (values
  ('22222222-0000-0000-0000-000000000001'::uuid),
  ('22222222-0000-0000-0000-000000000002'::uuid),
  ('22222222-0000-0000-0000-000000000003'::uuid),
  ('22222222-0000-0000-0000-000000000004'::uuid),
  ('22222222-0000-0000-0000-000000000005'::uuid),
  ('22222222-0000-0000-0000-000000000006'::uuid),
  ('22222222-0000-0000-0000-000000000007'::uuid),
  ('22222222-0000-0000-0000-000000000008'::uuid)
) as u(id)
cross join hostels h;

-- -----------------------------------------------------------------------------
-- TICKETS (50 rows, remapped from the original demo data onto the real
-- hotels and receptionists). Guest names/scenarios are unchanged.
-- -----------------------------------------------------------------------------
with raw_tickets (n, guest_name, reservation_number, hostel_name, channel, reason, priority,
                   description, status, agent_email, days_ago, resolve_after_hours,
                   resolution_notes, recontacted, recontacted_notes) as (
  values
  (1,  'Lucas Fernandez',   'RES-2026-0001', 'Rembrandt Square Hotel', 'call',      'check_in',     'medium', 'Guest arriving 3 hours before official check-in, asked if early check-in is possible.', 'resolved', 'l.regordosa@rb-horeca.com', 58, 1,  'Room was ready early, guest checked in without issue.', false, null),
  (2,  'Emma Thompson',     'RES-2026-0002', 'Rembrandt Square Hotel', 'whatsapp',  'reservation',  'low',    'Asking to confirm dorm bed reservation for 4 nights.', 'resolved', 'j.damian@rb-horeca.com', 57, 2,  'Confirmed reservation details via WhatsApp.', false, null),
  (3,  'Yuki Tanaka',       'RES-2026-0003', 'Rembrandt Square Hotel', 'email',     'payment',      'high',   'Card was charged twice for the same booking, requesting refund.', 'resolved', 'l.regordosa@rb-horeca.com', 56, 20, 'Duplicate charge confirmed and refunded, guest notified.', true, 'Guest called again 2 days later asking if refund had posted.'),
  (4,  'Liam OConnor',      'RES-2026-0004', 'Rembrandt Square Hotel', 'reception', 'access',       'medium', 'Key card stopped working after pool visit.', 'resolved', 'l.regordosa@rb-horeca.com', 55, 1,  'Recut key card at reception.', false, null),
  (5,  'Giulia Romano',       'RES-2026-0005', 'Durty Nellys',      'reception', 'maintenance',  'high',   'Air conditioning in room 12 not cooling.', 'resolved', 'l.regordosa@rb-horeca.com', 54, 6,  'Maintenance reset the unit, cooling restored.', false, null),
  (6,  'Mohammed Al-Farsi', 'RES-2026-0006', 'Durty Nellys',      'whatsapp',  'request',      'low',    'Requesting extra towels and a late checkout.', 'resolved', 'l.regordosa@rb-horeca.com', 53, 1,  'Extra towels delivered, late checkout granted until 13:00.', false, null),
  (7,  'Anna Kowalska',     'RES-2026-0007', 'Durty Nellys',      'call',      'complaint',    'urgent', 'Noise complaint from adjacent dorm room overnight.', 'resolved', 'l.regordosa@rb-horeca.com', 52, 3,  'Moved guest to a quieter room, spoke with noisy group.', true, 'Same guest reported noise again the following night.'),
  (8,  'Noah Andersson',    'RES-2026-0008', 'Durty Nellys',      'email',     'cancellation', 'medium', 'Wants to cancel due to flight change, asking about refund policy.', 'resolved', 'l.regordosa@rb-horeca.com', 51, 24, 'Cancellation processed per policy, partial refund issued.', false, null),
  (9,  'Chloe Martin',      'RES-2026-0009', 'Westlake',      'reception', 'check_in',     'low',    'Passport did not match booking name spelling.', 'resolved', 'j.damian@rb-horeca.com', 50, 1,  'Corrected spelling in booking, checked in normally.', false, null),
  (10, 'Diego Herrera',     'RES-2026-0010', 'Westlake',      'call',      'modification', 'medium', 'Wants to extend stay by two extra nights.', 'resolved', 'j.damian@rb-horeca.com', 49, 4,  'Extension confirmed, availability checked with PMS.', false, null),
  (11, 'Isabella Conti',    'RES-2026-0011', 'Westlake',      'whatsapp',  'payment',      'high',   'Deposit payment failed but booking shows as unpaid.', 'resolved', 'j.damian@rb-horeca.com', 48, 5,  'Payment link resent, guest completed payment successfully.', false, null),
  (12, 'Katarina Nemcova',   'RES-2026-0012', 'This Hostel',  'reception', 'access',       'medium', 'Locked out of room, key card demagnetized.', 'resolved', 'l.regordosa@rb-horeca.com', 47, 1,  'Reissued key card at front desk.', false, null),
  (13, 'Tomas Dvorak',      'RES-2026-0013', 'This Hostel',  'call',      'reservation',  'low',    'Group booking of 6 people, confirming bed layout.', 'resolved', 'l.regordosa@rb-horeca.com', 46, 2,  'Bed layout confirmed and emailed to group organizer.', false, null),
  (14, 'Stefan Brunner',       'RES-2026-0014', 'Rembrandt Square Hotel', 'email', 'maintenance', 'urgent', 'No hot water reported in the entire dorm wing.', 'resolved', 'j.damian@rb-horeca.com', 45, 8, 'Boiler issue fixed by on-call technician same day.', false, null),
  (15, 'Hana Kobayashi',    'RES-2026-0015', 'Rembrandt Square Hotel', 'reception', 'request', 'low', 'Asking for hiking trail recommendations and a packed lunch.', 'resolved', 'j.damian@rb-horeca.com', 44, 1, 'Provided trail map and coordinated packed lunch with kitchen.', false, null),
  (16, 'Isabel Navarro',       'RES-2026-0016', 'Rembrandt Square Hotel', 'call',      'complaint',    'high',   'Guest unhappy about cleanliness of shared bathroom.', 'resolved', 'l.regordosa@rb-horeca.com', 43, 3, 'Bathroom deep-cleaned, guest offered complimentary drink.', false, null),
  (17, 'Andres Molina',      'RES-2026-0017', 'Rembrandt Square Hotel', 'whatsapp',  'other',        'low',    'Asking about luggage storage after checkout.', 'in_progress', 'j.damian@rb-horeca.com', 6, null, null, false, null),
  (18, 'Ana Silva',         'RES-2026-0018', 'Durty Nellys',      'reception', 'check_in',     'medium', 'Early arrival, no rooms ready yet, requesting storage.', 'resolved', 'l.regordosa@rb-horeca.com', 42, 2, 'Luggage stored, guest checked in at 15:00 as scheduled.', false, null),
  (19, 'Ana  Silva',        'RES-2026-0044', 'Durty Nellys',      'email',     'payment',      'medium', 'Asking for an invoice copy for reimbursement purposes.', 'resolved', 'l.regordosa@rb-horeca.com', 12, 3, 'Invoice PDF emailed to guest.', false, null),
  (20, 'Helena Duarte',        'RES-2026-0019', 'Durty Nellys',      'call',      'cancellation', 'medium', 'Cancelling due to illness, has travel insurance.', 'resolved', 'l.regordosa@rb-horeca.com', 41, 2, 'Cancellation confirmed, insurance documentation provided.', false, null),
  (21, 'Bruno Martins',       'RES-2026-0020', 'Westlake',      'whatsapp',  'modification', 'low',    'Wants to switch from dorm bed to private room.', 'resolved', 'j.damian@rb-horeca.com', 40, 2, 'Upgraded to private room, price difference charged.', false, null),
  (22, 'Camille Dubois',    'RES-2026-0021', 'Westlake',      'reception', 'access',       'medium', 'Beach locker key lost.', 'resolved', 'j.damian@rb-horeca.com', 39, 1, 'Replacement lock issued, small fee applied.', false, null),
  (23, 'Marco Bianchi',     'RES-2026-0022', 'This Hostel',  'call',      'complaint',    'urgent', 'Reports bed bugs in dorm room, very upset.', 'resolved', 'l.regordosa@rb-horeca.com', 38, 10, 'Room inspected, pest control called, guest relocated to another hostel wing.', true, 'Guest raised the same concern again after moving rooms.'),
  (24, 'Grace Okafor',      'RES-2026-0023', 'This Hostel',  'email',     'reservation',  'low',    'Confirming breakfast is included in the rate.', 'resolved', 'l.regordosa@rb-horeca.com', 37, 1, 'Confirmed breakfast inclusion via email.', false, null),
  (25, 'Sven Johansson',    'RES-2026-0024', 'Rembrandt Square Hotel', 'reception', 'maintenance', 'medium', 'Window in room 5 does not close properly.', 'resolved', 'j.damian@rb-horeca.com', 36, 6, 'Window latch repaired by maintenance.', false, null),
  (26, 'Fatima Zahra',      'RES-2026-0025', 'Rembrandt Square Hotel', 'whatsapp', 'request', 'low', 'Asking about laundry service availability.', 'resolved', 'j.damian@rb-horeca.com', 35, 1, 'Explained self-service laundry hours and pricing.', false, null),
  (27, 'Lucas Fernandez',   'RES-2026-0026', 'Rembrandt Square Hotel', 'call',      'modification', 'medium', 'Returning guest wants to add 2 more nights to current stay.', 'resolved', 'l.regordosa@rb-horeca.com', 34, 3, 'Extension confirmed, room availability checked.', false, null),
  (28, 'Noor Abbas',        'RES-2026-0027', 'Rembrandt Square Hotel', 'reception', 'check_in',     'low',    'Guest arrived without printed confirmation.', 'resolved', 'j.damian@rb-horeca.com', 33, 1, 'Located booking by email, checked in normally.', false, null),
  (29, 'Ingrid Larsen',     'RES-2026-0028', 'Durty Nellys',      'email',     'cancellation', 'high',   'Requesting full refund citing hostel closed pool unexpectedly.', 'in_progress', 'l.regordosa@rb-horeca.com', 9, null, null, false, null),
  (30, 'Julien Moreau',     'RES-2026-0029', 'Durty Nellys',      'whatsapp',  'other',        'low',    'Asking for nearby pharmacy recommendations.', 'resolved', 'l.regordosa@rb-horeca.com', 32, 1, 'Sent list of nearby pharmacies and opening hours.', false, null),
  (31, 'Wei Zhang',         'RES-2026-0030', 'Westlake',      'call',      'payment',      'medium', 'Currency conversion looks incorrect on the invoice.', 'resolved', 'j.damian@rb-horeca.com', 31, 4, 'Recalculated invoice with correct exchange rate, corrected copy sent.', false, null),
  (32, 'Beatriz Costa',     'RES-2026-0031', 'Westlake',      'reception', 'access',       'low',    'Cannot get WiFi to connect in the room.', 'resolved', 'j.damian@rb-horeca.com', 30, 1, 'Reset router, provided correct WiFi password.', false, null),
  (33, 'Henrik Nilsson',    'RES-2026-0032', 'This Hostel',  'whatsapp',  'reservation',  'medium', 'Wants to confirm if pets are allowed for upcoming stay.', 'resolved', 'l.regordosa@rb-horeca.com', 29, 2, 'Informed guest pets are not allowed per hostel policy.', false, null),
  (34, 'Zainab Hussain',    'RES-2026-0033', 'This Hostel',  'call',      'complaint',    'medium', 'Reception staff was rude during check-in.', 'resolved', 'l.regordosa@rb-horeca.com', 28, 12, 'Apologized to guest, feedback logged for staff coaching.', false, null),
  (35, 'Oliver Schmidt',    'RES-2026-0034', 'Rembrandt Square Hotel', 'email', 'modification', 'low', 'Wants to change arrival date by one day.', 'resolved', 'j.damian@rb-horeca.com', 27, 3, 'Date changed in system, confirmation email sent.', false, null),
  (36, 'Priya Sharma',      'RES-2026-0035', 'Rembrandt Square Hotel', 'reception', 'maintenance', 'high', 'Shower drain clogged in shared bathroom.', 'resolved', 'j.damian@rb-horeca.com', 26, 5, 'Plumber cleared the drain same day.', false, null),
  (37, 'Giulia Romano',       'RES-2026-0036', 'Durty Nellys',      'call',      'request',      'low',    'Asking for a taxi to be booked to the airport.', 'resolved', 'l.regordosa@rb-horeca.com', 25, 1, 'Taxi booked for requested time.', false, null),
  (38, 'Ahmed Hassan',      'RES-2026-0037', 'Rembrandt Square Hotel', 'whatsapp',  'payment',      'urgent', 'Booking site shows paid, hostel PMS shows unpaid.', 'resolved', 'l.regordosa@rb-horeca.com', 24, 6, 'Confirmed with booking channel, payment matched manually in PMS.', false, null),
  (39, 'Laura Jimenez',     'RES-2026-0038', 'Rembrandt Square Hotel', 'reception', 'check_in',     'medium', 'Guest is a minor traveling with an ID document question.', 'resolved', 'j.damian@rb-horeca.com', 23, 2, 'Verified guardian consent form, checked in per policy.', false, null),
  (40, 'Viktor Petrov',     'RES-2026-0039', 'Westlake',      'email',     'cancellation', 'low',    'No-show due to missed flight connection, asking about policy.', 'closed', 'j.damian@rb-horeca.com', 22, 20, 'No-show fee applied per policy, case closed.', false, null),
  (41, 'Meera Nair',        'RES-2026-0040', 'Westlake',      'call',      'other',        'low',    'Asking if the hostel organizes surf lessons.', 'resolved', 'j.damian@rb-horeca.com', 21, 1, 'Shared partner surf school contact info.', false, null),
  (42, 'Karim Benali',      'RES-2026-0041', 'This Hostel',  'whatsapp',  'access',       'medium', 'Front door code is not working at night entrance.', 'resolved', 'l.regordosa@rb-horeca.com', 20, 2, 'Updated door code and re-sent to all current guests.', false, null),
  (43, 'Olga Ivanova',      'RES-2026-0042', 'This Hostel',  'reception', 'complaint',    'high',   'Overbooked dorm, guest has no assigned bed.', 'resolved', 'l.regordosa@rb-horeca.com', 19, 4, 'Relocated guest to upgraded room at no extra charge.', false, null),
  (44, 'Daniel Kim',        'RES-2026-0043', 'Rembrandt Square Hotel', 'email', 'reservation', 'low', 'Confirming cancellation policy before booking a group trip.', 'resolved', 'j.damian@rb-horeca.com', 18, 1, 'Cancellation policy explained in detail via email.', false, null),
  (45, 'Amara Nwosu',       'RES-2026-0045', 'Rembrandt Square Hotel', 'call', 'modification', 'medium', 'Wants to add one more guest to existing private room booking.', 'open', 'j.damian@rb-horeca.com', 4, null, null, false, null),
  (46, 'Yusuf Demir',       'RES-2026-0046', 'Rembrandt Square Hotel', 'reception', 'access',       'low',    'Safe box code forgotten, needs reset.', 'open', 'l.regordosa@rb-horeca.com', 3, null, null, false, null),
  (47, 'Ines Ferreira',     'RES-2026-0047', 'Durty Nellys',      'whatsapp',  'request',      'medium', 'Requesting a late checkout for a flight at midnight.', 'open', 'l.regordosa@rb-horeca.com', 2, null, null, false, null),
  (48, 'Fernando Castro',     'RES-2026-0048', 'Westlake',      'call',      'payment',      'high',   'Refund promised last week has not appeared in guest account.', 'in_progress', 'j.damian@rb-horeca.com', 5, null, null, false, null),
  (49, 'Eva Kralova',     'RES-2026-0049', 'This Hostel',  'email',     'complaint',    'urgent', 'Guest reporting theft from locker, requesting police report assistance.', 'open', 'l.regordosa@rb-horeca.com', 1, null, null, false, null),
  (50, 'Elif Yildiz',       'RES-2026-0050', 'Rembrandt Square Hotel', 'reception', 'check_in', 'low', 'Wheelchair accessibility question before arrival.', 'open', 'j.damian@rb-horeca.com', 0, null, null, false, null)
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
-- GUESTS (golden records) — same aggregation logic as the original seed.
-- -----------------------------------------------------------------------------
insert into guests (full_name, total_tickets, last_contact_at, common_reasons, preferred_channel, linked_reservations, data_quality_score, email, phone)
select
  t.guest_name,
  count(*),
  max(t.created_at),
  array_agg(distinct t.reason),
  (array_agg(t.channel order by t.created_at desc))[1],
  array_agg(distinct t.reservation_number),
  least(100,
    (case when count(distinct t.reservation_number) > 0 then 50 else 0 end) +
    (case when count(*) > 1 then 30 else 0 end) +
    (case when t.guest_name like '% %' then 20 else 0 end)
  ),
  null,
  null
from tickets t
group by t.guest_name;

update tickets t
set guest_id = g.id
from guests g
where g.full_name = t.guest_name;

-- -----------------------------------------------------------------------------
-- DEDUP REVIEW QUEUE — same "Ana Silva" vs "Ana  Silva" demo pair.
-- -----------------------------------------------------------------------------
insert into guest_merge_candidates (guest_id_a, guest_id_b, match_score, match_reason, status)
select g1.id, g2.id, 92.50, 'Name match (normalized) + same hostel + overlapping reason (payment/check-in)', 'pending'
from guests g1, guests g2
where g1.full_name = 'Ana Silva' and g2.full_name = 'Ana  Silva';

-- -----------------------------------------------------------------------------
-- TICKET HISTORY
-- -----------------------------------------------------------------------------
insert into ticket_history (ticket_id, changed_by, field_name, old_value, new_value, created_at)
select t.id, t.assignee_id, 'status', 'open', 'resolved', t.resolved_at
from tickets t
where t.status in ('resolved', 'closed') and t.resolved_at is not null;

insert into ticket_history (ticket_id, changed_by, field_name, old_value, new_value, created_at)
select t.id, t.assignee_id, 'status', 'open', 'in_progress', t.created_at + interval '1 hour'
from tickets t
where t.status = 'in_progress';

-- -----------------------------------------------------------------------------
-- MAINTENANCE TICKETS (sample data, all reported by Robin M)
-- -----------------------------------------------------------------------------
with raw_maintenance (hostel_name, title, description, status, priority, days_ago, resolve_after_hours) as (
  values
  ('Rembrandt Square Hotel', 'Leaking faucet in room 204',        'Bathroom sink faucet drips constantly, needs a new washer or cartridge.', 'open',        'medium', 4,    null),
  ('Rembrandt Square Hotel', 'Broken window latch in common room', 'Window in the lounge does not latch shut, security concern overnight.',  'in_progress', 'low',    2,    null),
  ('Durty Nellys',           'AC unit not cooling in dorm 3',      'Air conditioning unit blows warm air, likely needs refrigerant recharge.', 'resolved',    'high',   10,   6),
  ('Durty Nellys',           'Loose handrail on staircase',        'Handrail between floors 1 and 2 is loose, trip/fall hazard.',             'open',        'urgent', 1,    null),
  ('This Hostel',            'WiFi router needs replacement',      'Router in the reception area keeps dropping connection, guests complaining.', 'in_progress', 'medium', 3, null),
  ('This Hostel',            'Light fixture flickering in hallway','Hallway light on 2nd floor flickers, ballast likely needs replacing.',    'closed',      'low',    15,   4),
  ('Westlake',               'Water heater malfunction',           'No hot water in the east wing, boiler pressure reading low.',              'open',        'high',   0,    null),
  ('Westlake',               'Door lock sticking on room 12',      'Key card lock on room 12 sticks and takes several tries to open.',        'resolved',    'medium', 6,    2)
)
insert into maintenance_tickets (hostel_id, title, description, status, priority, created_by, created_at, resolved_at)
select
  h.id, rm.title, rm.description, rm.status::maintenance_status, rm.priority::maintenance_priority,
  '22222222-0000-0000-0000-000000000008',
  now() - (rm.days_ago || ' days')::interval,
  case when rm.resolve_after_hours is not null
    then now() - (rm.days_ago || ' days')::interval + (rm.resolve_after_hours || ' hours')::interval
    else null
  end
from raw_maintenance rm
join hostels h on h.name = rm.hostel_name;
