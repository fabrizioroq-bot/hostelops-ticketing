from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.security import CurrentUser
from app.models.schemas import MaintenancePriority, MaintenanceStatus, MaintenanceTicketCreate, MaintenanceTicketUpdate
from app.services import maintenance_service


@pytest.fixture(autouse=True)
def _patch_audit(monkeypatch):
    calls = []
    monkeypatch.setattr(maintenance_service, "log_audit", lambda *a, **k: calls.append(a))
    return calls


def _user(role, hostel_ids):
    return CurrentUser(
        id=uuid4(), email=f"{role}@rb-horeca.com", full_name=role.title(), role=role,
        is_active=True, hostel_ids=[str(h) for h in hostel_ids], access_token="t",
    )


def _payload(hostel_id):
    return MaintenanceTicketCreate(hostel_id=hostel_id, title="Leaking pipe", description="Under the sink.")


def test_maintenance_role_cannot_create_ticket_outside_assigned_hostel(fake_client):
    allowed_hostel = uuid4()
    other_hostel = uuid4()
    robin = _user("maintenance", [allowed_hostel])

    with pytest.raises(HTTPException) as exc_info:
        maintenance_service.create_ticket(robin, fake_client, _payload(other_hostel))
    assert exc_info.value.status_code == 403


def test_maintenance_role_can_create_ticket_for_assigned_hostel(fake_client):
    hostel_id = uuid4()
    robin = _user("maintenance", [hostel_id])

    ticket = maintenance_service.create_ticket(robin, fake_client, _payload(hostel_id))

    assert ticket["created_by"] == str(robin.id)
    assert ticket["hostel_id"] == str(hostel_id)
    assert ticket["title"] == "Leaking pipe"


def test_admin_can_create_ticket_for_any_hostel(fake_client):
    admin = _user("admin", [])  # admins have no explicit hostel assignments
    ticket = maintenance_service.create_ticket(admin, fake_client, _payload(uuid4()))
    assert ticket["created_by"] == str(admin.id)


def test_update_ticket_status_and_priority(fake_client, _patch_audit):
    hostel_id = uuid4()
    robin = _user("maintenance", [hostel_id])
    ticket = maintenance_service.create_ticket(robin, fake_client, _payload(hostel_id))

    updated = maintenance_service.update_ticket(
        robin, fake_client, ticket["id"],
        MaintenanceTicketUpdate(status=MaintenanceStatus.in_progress, priority=MaintenancePriority.high),
    )

    assert updated["status"] == "in_progress"
    assert updated["priority"] == "high"
    audit_actions = [call[1] for call in _patch_audit]
    assert "maintenance_ticket_updated" in audit_actions


def test_updating_nonexistent_ticket_raises_404(fake_client):
    robin = _user("maintenance", [uuid4()])
    with pytest.raises(HTTPException) as exc_info:
        maintenance_service.update_ticket(
            robin, fake_client, uuid4(), MaintenanceTicketUpdate(status=MaintenanceStatus.resolved)
        )
    assert exc_info.value.status_code == 404
