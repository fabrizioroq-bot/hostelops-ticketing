"""Shared test fixtures.

Sets dummy Supabase environment variables *before* any application module
is imported, so `Settings()` (which requires these as non-optional fields)
never fails during test collection, and provides a minimal in-memory fake
of the supabase-py query builder chain so service-layer logic can be
tested without a live Supabase project.
"""
import os
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "unit-test-jwt-secret-do-not-use-in-prod")

import pytest  # noqa: E402

from app.core.security import CurrentUser  # noqa: E402


class FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    def __init__(self, table: "FakeTable", op: str, payload=None):
        self._table = table
        self._op = op
        self._payload = payload
        self._filters: list[tuple] = []
        self._single = False

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def is_(self, col, val):
        self._filters.append(("is", col, val))
        return self

    def contains(self, col, val):
        self._filters.append(("contains", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, vals))
        return self

    def ilike(self, col, pattern):
        self._filters.append(("ilike", col, pattern))
        return self

    def or_(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def single(self):
        self._single = True
        return self

    def _matching_rows(self):
        rows = self._table.rows
        for kind, col, val in self._filters:
            if kind == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif kind == "in":
                rows = [r for r in rows if r.get(col) in val]
            elif kind == "ilike":
                needle = val.strip("%").lower()
                rows = [r for r in rows if needle in str(r.get(col, "")).lower()]
            elif kind == "contains":
                rows = [r for r in rows if val[0] in (r.get(col) or [])]
            elif kind == "is" and val == "null":
                rows = [r for r in rows if r.get(col) is None]
        return rows

    def execute(self) -> FakeResult:
        # Every branch returns *copies*, never live references into
        # self._table.rows — this mirrors real supabase-py/PostgREST, where
        # each `.execute()` is a network round-trip yielding a fresh
        # snapshot. Callers that hold on to an earlier result (e.g. the
        # "existing" row fetched before an update) must not see later
        # mutations leak backwards through a shared dict reference.
        if self._op == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            created = []
            for p in payloads:
                row = {**p}
                row.setdefault("id", str(uuid4()))
                self._table.rows.append(row)
                created.append(dict(row))
            return FakeResult(created)

        if self._op == "update":
            matched = self._matching_rows()
            for row in matched:
                row.update(self._payload)
            return FakeResult([dict(r) for r in matched])

        if self._op == "delete":
            matched = self._matching_rows()
            self._table.rows = [r for r in self._table.rows if r not in matched]
            return FakeResult([dict(r) for r in matched])

        matched = self._matching_rows()
        if self._single:
            return FakeResult(dict(matched[0]) if matched else None)
        return FakeResult([dict(r) for r in matched], count=len(matched))


class FakeTable:
    def __init__(self):
        self.rows: list[dict] = []

    def select(self, *_args, **_kwargs):
        return FakeQuery(self, "select")

    def insert(self, payload):
        return FakeQuery(self, "insert", payload)

    def update(self, payload):
        return FakeQuery(self, "update", payload)

    def delete(self):
        return FakeQuery(self, "delete")


class FakeClient:
    """Fakes the subset of the supabase-py `Client` interface our services
    use: `.table(name)`. RPC calls are not faked here (dashboard tests, if
    added, should stub `app.services.dashboard_service` functions directly)."""

    def __init__(self):
        self._tables: dict[str, FakeTable] = {}

    def table(self, name: str) -> FakeTable:
        return self._tables.setdefault(name, FakeTable())


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def agent_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="agent.test@hostelops.example",
        full_name="Test Agent",
        role="agent",
        is_active=True,
        hostel_ids=[],
        access_token="fake-token",
    )


@pytest.fixture
def admin_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="admin.test@hostelops.example",
        full_name="Test Admin",
        role="admin",
        is_active=True,
        hostel_ids=[],
        access_token="fake-token",
    )
