"""
Supabase client wrapper.
In Phase 1 (prototype) this is a no-op shim — the app uses in-memory storage.
Wire up SUPABASE_URL and SUPABASE_ANON_KEY env vars when connecting to real DB.
"""

import os
from typing import Optional

# Lazy import — only needed when Supabase env vars are present
_client = None


def get_supabase_client():
    """Return a Supabase client, or None if env vars are not set."""
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_ANON_KEY", "")

    if not url or not key:
        return None

    try:
        from supabase import create_client  # type: ignore
        _client = create_client(url, key)
        return _client
    except ImportError:
        # supabase-py not installed — that's fine for local dev
        return None


def is_connected() -> bool:
    return get_supabase_client() is not None
