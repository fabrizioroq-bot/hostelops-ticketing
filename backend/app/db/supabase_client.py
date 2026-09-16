"""Supabase client factories.

Two distinct trust levels are used throughout the backend:

1. `get_service_client()` — uses the SERVICE ROLE key, which bypasses Row
   Level Security entirely. Reserved for operations that are intentionally
   privileged and always mediated by an application-level role check first:
   audit log writes, ticket history writes, user provisioning (Supabase Admin
   API), guest golden-record merges, and cross-hostel MDM matching. Every
   call site using this client must have already verified the caller's role.

2. `get_user_client(access_token)` — uses the ANON key plus the caller's own
   JWT, so every query runs AS that user and is still subject to Postgres
   Row Level Security. This is the default for ordinary reads/writes, giving
   defense-in-depth: even a bug in the backend's own role checks cannot leak
   data across hostels or roles because the database itself enforces it.
"""
from functools import lru_cache

from supabase import create_client, Client

from app.core.config import get_settings


@lru_cache
def get_service_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_user_client(access_token: str) -> Client:
    """Build a request-scoped client that acts as the authenticated user.

    Not cached: each request carries a different token, and the client is
    cheap to construct (no network call happens until a query is issued).
    """
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
