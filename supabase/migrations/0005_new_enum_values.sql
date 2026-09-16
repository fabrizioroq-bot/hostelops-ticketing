-- =============================================================================
-- New enum values for the Maintenance module. Split into its own migration
-- (rather than bundled with the tables that use these values) because
-- Postgres requires a new enum value to be committed before it can be used
-- in the same session — keeping this as a standalone file/statement avoids
-- any ordering ambiguity.
-- =============================================================================
alter type user_role add value 'maintenance';
alter type audit_action add value 'maintenance_ticket_created';
alter type audit_action add value 'maintenance_ticket_updated';
