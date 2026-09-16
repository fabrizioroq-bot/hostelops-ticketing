import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.core.config import get_settings
from app.core.security import get_current_user, require_roles, CurrentUser


def _make_token(user_id: str, secret: str) -> str:
    return jwt.encode({"sub": user_id, "aud": "authenticated"}, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_invalid_token_raises_401():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-real-jwt")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_valid_token_but_unknown_profile_raises_401(monkeypatch):
    from app.tests.conftest import FakeClient

    fake_client = FakeClient()  # no app_users rows seeded
    monkeypatch.setattr("app.core.security.get_service_client", lambda: fake_client)

    token = _make_token("11111111-1111-1111-1111-111111111111", get_settings().supabase_jwt_secret)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_deactivated_user_raises_403(monkeypatch):
    from app.tests.conftest import FakeClient

    fake_client = FakeClient()
    user_id = "22222222-2222-2222-2222-222222222222"
    fake_client.table("app_users").rows.append(
        {"id": user_id, "email": "x@example.com", "full_name": "X", "role": "agent", "is_active": False}
    )
    monkeypatch.setattr("app.core.security.get_service_client", lambda: fake_client)

    token = _make_token(user_id, get_settings().supabase_jwt_secret)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_valid_active_user_resolves_role_and_hostels(monkeypatch):
    from app.tests.conftest import FakeClient

    fake_client = FakeClient()
    user_id = "33333333-3333-3333-3333-333333333333"
    hostel_id = "44444444-4444-4444-4444-444444444444"
    fake_client.table("app_users").rows.append(
        {"id": user_id, "email": "agent@example.com", "full_name": "Agent Name", "role": "agent", "is_active": True}
    )
    fake_client.table("user_hostels").rows.append({"user_id": user_id, "hostel_id": hostel_id})
    monkeypatch.setattr("app.core.security.get_service_client", lambda: fake_client)

    token = _make_token(user_id, get_settings().supabase_jwt_secret)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    user = await get_current_user(creds)
    assert user.role == "agent"
    assert user.hostel_ids == [hostel_id]


@pytest.mark.asyncio
async def test_require_roles_rejects_wrong_role():
    checker = require_roles("admin")
    agent = CurrentUser(
        id="1", email="a@x.com", full_name="A", role="agent", is_active=True, hostel_ids=[], access_token="t"
    )
    with pytest.raises(HTTPException) as exc_info:
        await checker(agent)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_roles_allows_matching_role():
    checker = require_roles("admin", "supervisor")
    admin = CurrentUser(
        id="1", email="a@x.com", full_name="A", role="admin", is_active=True, hostel_ids=[], access_token="t"
    )
    result = await checker(admin)
    assert result is admin
