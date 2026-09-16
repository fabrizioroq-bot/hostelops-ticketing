"""Adapter interface for Property Management System / channel manager
integrations. New providers (Cloudbeds, Little Hotelier, ...) implement
this interface and register in `pms_service.ADAPTERS`, so the rest of the
codebase never depends on a specific PMS's request/response shape.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypedDict


class NormalizedReservation(TypedDict):
    reservation_number: str
    guest_name: str
    guest_email: str | None
    guest_phone: str | None
    check_in: str | None
    check_out: str | None
    status: str | None


class PMSAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def test_connection(self, property_external_id: str, access_token: str) -> bool:
        """Verify the stored credentials are valid for this property."""

    @abstractmethod
    async def fetch_reservations(
        self, property_external_id: str, access_token: str, start: datetime, end: datetime
    ) -> list[NormalizedReservation]:
        """Fetch reservations in [start, end], normalized to a common shape."""
