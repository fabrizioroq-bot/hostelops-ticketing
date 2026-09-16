// Mirrors backend/app/models/schemas.py — keep in sync.

export type UserRole = "admin" | "supervisor" | "agent";

export type TicketChannel = "call" | "whatsapp" | "email" | "reception" | "other";

export type TicketReason =
  | "reservation" | "payment" | "check_in" | "access" | "maintenance"
  | "request" | "complaint" | "cancellation" | "modification" | "other";

export type TicketPriority = "low" | "medium" | "high" | "urgent";

export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";

export type PmsSyncStatus = "not_integrated" | "pending" | "synced" | "error";

export type DedupReviewStatus = "pending" | "approved" | "rejected";

export interface Ticket {
  id: string;
  reservation_number: string | null;
  guest_name: string;
  guest_id: string | null;
  hostel_id: string;
  channel: TicketChannel;
  reason: TicketReason;
  priority: TicketPriority;
  description: string;
  status: TicketStatus;
  assignee_id: string;
  created_by: string;
  resolution_notes: string | null;
  recontacted: boolean;
  recontacted_notes: string | null;
  created_at: string;
  resolved_at: string | null;
  updated_at: string;
}

export interface TicketHistoryEntry {
  id: string;
  ticket_id: string;
  changed_by: string | null;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export interface Guest {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  total_tickets: number;
  last_contact_at: string | null;
  common_reasons: string[];
  preferred_channel: string | null;
  linked_reservations: string[];
  data_quality_score: number;
  merged_into: string | null;
  created_at: string;
}

export interface MergeCandidate {
  id: string;
  guest_id_a: string;
  guest_id_b: string;
  match_score: number;
  match_reason: string;
  status: DedupReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface Hostel {
  id: string;
  name: string;
  location: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  pms_status: PmsSyncStatus;
  pms_provider: string | null;
  pms_external_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AppUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  hostel_ids: string[];
  created_at: string;
}

export interface CurrentUserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  hostel_ids: string[];
}

export interface PaginatedTickets {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardOverview {
  total: number;
  open: number;
  in_progress: number;
  resolved: number;
  closed: number;
  today: number;
  this_week: number;
  this_month: number;
}
