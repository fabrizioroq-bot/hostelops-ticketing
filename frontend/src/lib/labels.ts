import type { TicketPriority, TicketStatus, TicketReason, TicketChannel } from "../types";

export const STATUS_COLOR: Record<TicketStatus, string> = {
  open: "blue",
  in_progress: "yellow",
  resolved: "green",
  closed: "gray",
};

export const PRIORITY_COLOR: Record<TicketPriority, string> = {
  low: "gray",
  medium: "blue",
  high: "orange",
  urgent: "red",
};

export const REASON_LABEL: Record<TicketReason, string> = {
  reservation: "Reservation",
  payment: "Payment",
  check_in: "Check-in",
  access: "Access",
  maintenance: "Maintenance",
  request: "Request",
  complaint: "Complaint",
  cancellation: "Cancellation",
  modification: "Modification",
  other: "Other",
};

export const CHANNEL_LABEL: Record<TicketChannel, string> = {
  call: "Call",
  whatsapp: "WhatsApp",
  email: "Email",
  reception: "Reception",
  other: "Other",
};

export const STATUS_LABEL: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
};

export function humanize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " ");
}
