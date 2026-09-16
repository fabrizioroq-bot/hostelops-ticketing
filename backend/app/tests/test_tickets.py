from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.security import CurrentUser
from app.models.schemas import TicketCreate, TicketUpdate, TicketChannel, TicketReason, TicketPriority, TicketStatus
from app.services import ticket_service


@pytest.fixture(autouse=True)
def _patch_mdm_and_audit(monkeypatch):
    """Ticket creation/update orchestrates guest MDM sync and audit logging
    as side effects; those are covered by their own service tests, so here
    we stub them and assert only the ticket business rules."""
    fixed_guest_id = uuid4()
    monkeypatch.setattr(
        ticket_service, "find_or_create_guest", lambda name, res_num: (fixed_guest_id, True)
    )
    monkeypatch.setattr(ticket_service, "sync_guest_after_ticket", lambda *a, **k: None)

    audit_calls = []
    monkeypatch.setattr(ticket_service, "log_audit", lambda *a, **k: audit_calls.append(a))
    history_calls = []
    monkeypatch.setattr(ticket_service, "log_ticket_history", lambda *a, **k: history_calls.append(a))
    return {"audit_calls": audit_calls, "history_calls": history_calls, "guest_id": fixed_guest_id}


def _agent(hostel_ids):
    return CurrentUser(
        id=uuid4(), email="agent@x.com", full_name="Agent", role="agent",
        is_active=True, hostel_ids=[str(h) for h in hostel_ids], access_token="t",
    )


def _ticket_payload(hostel_id):
    return TicketCreate(
        guest_name="Jane Traveler",
        reservation_number="RES-TEST-001",
        hostel_id=hostel_id,
        channel=TicketChannel.call,
        reason=TicketReason.check_in,
        priority=TicketPriority.medium,
        description="Test ticket description.",
    )


def test_agent_cannot_create_ticket_outside_assigned_hostel(fake_client):
    allowed_hostel = uuid4()
    other_hostel = uuid4()
    agent = _agent([allowed_hostel])

    with pytest.raises(HTTPException) as exc_info:
        ticket_service.create_ticket(agent, fake_client, _ticket_payload(other_hostel))
    assert exc_info.value.status_code == 403


def test_agent_can_create_ticket_for_assigned_hostel(fake_client):
    hostel_id = uuid4()
    agent = _agent([hostel_id])

    ticket = ticket_service.create_ticket(agent, fake_client, _ticket_payload(hostel_id))

    assert ticket["assignee_id"] == str(agent.id)
    assert ticket["created_by"] == str(agent.id)
    assert ticket["guest_name"] == "Jane Traveler"
    assert fake_client.table("tickets").rows[0]["hostel_id"] == str(hostel_id)


def test_agent_cannot_reassign_ticket(fake_client):
    hostel_id = uuid4()
    agent = _agent([hostel_id])
    ticket = ticket_service.create_ticket(agent, fake_client, _ticket_payload(hostel_id))

    with pytest.raises(HTTPException) as exc_info:
        ticket_service.update_ticket(
            agent, fake_client, ticket["id"], TicketUpdate(assignee_id=uuid4())
        )
    assert exc_info.value.status_code == 403


def test_agent_can_update_status_and_resolution(fake_client, _patch_mdm_and_audit):
    hostel_id = uuid4()
    agent = _agent([hostel_id])
    ticket = ticket_service.create_ticket(agent, fake_client, _ticket_payload(hostel_id))
    # Postgres defaults `status` to 'open' on insert (see migration
    # 0001_init.sql); the fake insert doesn't apply column defaults, so set
    # it explicitly to mirror real DB behavior for this transition test.
    fake_client.table("tickets").rows[0]["status"] = "open"
    fake_client.table("guests").rows.append({"id": str(_patch_mdm_and_audit["guest_id"])})

    updated = ticket_service.update_ticket(
        agent, fake_client, ticket["id"],
        TicketUpdate(status=TicketStatus.resolved, resolution_notes="Fixed at reception."),
    )

    assert updated["status"] == "resolved"
    assert updated["resolution_notes"] == "Fixed at reception."
    audit_actions = [call[1] for call in _patch_mdm_and_audit["audit_calls"]]
    assert "ticket_resolved" in audit_actions


def test_updating_nonexistent_ticket_raises_404(fake_client):
    agent = _agent([uuid4()])
    with pytest.raises(HTTPException) as exc_info:
        ticket_service.update_ticket(agent, fake_client, uuid4(), TicketUpdate(status=TicketStatus.in_progress))
    assert exc_info.value.status_code == 404
