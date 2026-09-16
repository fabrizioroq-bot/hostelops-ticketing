"""Mews Connector API v1 adapter.

Mews authenticates every request with three values in the JSON body
(there is no OAuth bearer header): `ClientToken` (identifies this
integration, shared across all properties), `AccessToken` (identifies one
specific Mews Enterprise/property), and `Client` (a free-text string
identifying the calling application, per Mews' integration guidelines).

Docs: https://mews-systems.gitbook.io/connector-api
"""
from datetime import datetime

import httpx

from app.core.config import get_settings
from app.services.pms.base import NormalizedReservation, PMSAdapter

_CLIENT_IDENTIFIER = "HostelOps Ticketing Integration 1.0"


class MewsAdapter(PMSAdapter):
    provider_name = "mews"

    def __init__(self) -> None:
        self._base_url = get_settings().mews_base_url
        self._client_token = get_settings().mews_client_token

    def _base_payload(self, access_token: str) -> dict:
        return {
            "ClientToken": self._client_token,
            "AccessToken": access_token,
            "Client": _CLIENT_IDENTIFIER,
        }

    async def test_connection(self, property_external_id: str, access_token: str) -> bool:
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                f"{self._base_url}/configuration/get",
                json=self._base_payload(access_token),
            )
        return resp.status_code == 200

    async def fetch_reservations(
        self, property_external_id: str, access_token: str, start: datetime, end: datetime
    ) -> list[NormalizedReservation]:
        payload = {
            **self._base_payload(access_token),
            "CollidingUtc": {"StartUtc": start.isoformat(), "EndUtc": end.isoformat()},
            "Extent": {"Customers": True, "ReservationGroups": True},
        }
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(f"{self._base_url}/reservations/getAll", json=payload)
            resp.raise_for_status()
            body = resp.json()

        customers_by_id = {c["Id"]: c for c in body.get("Customers", [])}
        normalized: list[NormalizedReservation] = []
        for reservation in body.get("Reservations", []):
            customer = customers_by_id.get(reservation.get("CustomerId"), {})
            full_name = " ".join(
                filter(None, [customer.get("FirstName"), customer.get("LastName")])
            ) or "Unknown Guest"
            normalized.append(
                {
                    "reservation_number": reservation.get("Number") or reservation.get("Id"),
                    "guest_name": full_name,
                    "guest_email": customer.get("Email"),
                    "guest_phone": customer.get("Phone"),
                    "check_in": reservation.get("StartUtc"),
                    "check_out": reservation.get("EndUtc"),
                    "status": reservation.get("State"),
                }
            )
        return normalized
