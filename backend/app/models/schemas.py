"""Pydantic request/response models. Enums mirror the Postgres enum types
defined in supabase/migrations/0001_init.sql — keep them in sync.
"""
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    admin = "admin"
    supervisor = "supervisor"
    agent = "agent"


class TicketChannel(str, Enum):
    call = "call"
    whatsapp = "whatsapp"
    email = "email"
    reception = "reception"
    other = "other"


class TicketReason(str, Enum):
    reservation = "reservation"
    payment = "payment"
    check_in = "check_in"
    access = "access"
    maintenance = "maintenance"
    request = "request"
    complaint = "complaint"
    cancellation = "cancellation"
    modification = "modification"
    other = "other"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class PmsSyncStatus(str, Enum):
    not_integrated = "not_integrated"
    pending = "pending"
    synced = "synced"
    error = "error"


class DedupReviewStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------
class TicketCreate(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=200)
    reservation_number: str | None = Field(None, max_length=100)
    hostel_id: UUID
    channel: TicketChannel
    reason: TicketReason
    priority: TicketPriority = TicketPriority.medium
    description: str = Field(..., min_length=1, max_length=500)


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    resolution_notes: str | None = Field(None, max_length=2000)
    recontacted: bool | None = None
    recontacted_notes: str | None = Field(None, max_length=1000)
    assignee_id: UUID | None = None  # admin/supervisor only — enforced in service layer

    @field_validator("resolution_notes")
    @classmethod
    def strip_notes(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class TicketOut(BaseModel):
    id: UUID
    reservation_number: str | None
    guest_name: str
    guest_id: UUID | None
    hostel_id: UUID
    channel: TicketChannel
    reason: TicketReason
    priority: TicketPriority
    description: str
    status: TicketStatus
    assignee_id: UUID
    created_by: UUID
    resolution_notes: str | None
    recontacted: bool
    recontacted_notes: str | None
    created_at: datetime
    resolved_at: datetime | None
    updated_at: datetime


class TicketHistoryEntry(BaseModel):
    id: UUID
    ticket_id: UUID
    changed_by: UUID | None
    field_name: str
    old_value: str | None
    new_value: str | None
    created_at: datetime


class TicketFilters(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    channel: TicketChannel | None = None
    reason: TicketReason | None = None
    hostel_id: UUID | None = None
    assignee_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    search: str | None = None  # matches guest_name or reservation_number
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=200)


# ---------------------------------------------------------------------------
# Guests (MDM golden records)
# ---------------------------------------------------------------------------
class GuestOut(BaseModel):
    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    total_tickets: int
    last_contact_at: datetime | None
    common_reasons: list[str]
    preferred_channel: str | None
    linked_reservations: list[str]
    data_quality_score: int
    merged_into: UUID | None
    created_at: datetime


class GuestUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)


class MergeCandidateOut(BaseModel):
    id: UUID
    guest_id_a: UUID
    guest_id_b: UUID
    match_score: float
    match_reason: str
    status: DedupReviewStatus
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Hostels
# ---------------------------------------------------------------------------
class HostelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    location: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    pms_provider: str | None = None
    pms_external_id: str | None = None


class HostelUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    pms_status: PmsSyncStatus | None = None
    pms_provider: str | None = None
    pms_external_id: str | None = None
    is_active: bool | None = None


class HostelOut(BaseModel):
    id: UUID
    name: str
    location: str | None
    contact_email: str | None
    contact_phone: str | None
    pms_status: PmsSyncStatus
    pms_provider: str | None
    pms_external_id: str | None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=200)
    role: UserRole
    hostel_ids: list[UUID] = Field(default_factory=list)
    temporary_password: str = Field(..., min_length=12)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    hostel_ids: list[UUID] | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    hostel_ids: list[UUID]
    created_at: datetime


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------
class DashboardFilters(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    hostel_id: UUID | None = None
    assignee_id: UUID | None = None
    priority: TicketPriority | None = None
    reason: TicketReason | None = None


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
class ExportColumns(BaseModel):
    columns: list[str] | None = None  # None = all default columns
