"""In-memory session and user preference store for multi-turn conversations."""

from __future__ import annotations

from typing import Any

# In-memory storage for active sessions, user preferences, and field claims
_SESSIONS: dict[str, list[dict[str, Any]]] = {}
_USER_PREFERENCES: dict[str, dict[str, Any]] = {
    # Default preferences for Nathan Pierce (U-601):
    # Sort wells by area then well ID; format costs in thousands ($k)
    "U-601": {
        "sort_by": ["area_id", "asset_id"],
        "cost_format": "thousands",
    },
    "Nathan Pierce": {
        "sort_by": ["area_id", "asset_id"],
        "cost_format": "thousands",
    },
}

_CLAIMS: list[dict[str, Any]] = []


def record_turn(
    session_id: str,
    user_id: str | None,
    user_name: str | None,
    question: str,
    response_data: dict[str, Any],
) -> None:
    """Records a conversation turn under the specified session ID."""
    if not session_id:
        return
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = []

    _SESSIONS[session_id].append(
        {
            "user_id": user_id,
            "user_name": user_name,
            "question": question,
            "response": response_data,
        }
    )


def get_session_history(session_id: str | None) -> list[dict[str, Any]]:
    """Retrieves all turns for a given session."""
    if not session_id or session_id not in _SESSIONS:
        return []
    return _SESSIONS[session_id]


def get_last_turn(session_id: str | None) -> dict[str, Any] | None:
    """Returns the most recent turn in the specified session."""
    history = get_session_history(session_id)
    if history:
        return history[-1]
    return None


def get_user_preferences(user_key: str | None) -> dict[str, Any]:
    """Retrieves formatting and sorting preferences for a user."""
    if not user_key:
        return {}
    return _USER_PREFERENCES.get(user_key, {})


def set_user_preference(user_key: str, pref_key: str, pref_value: Any) -> None:
    """Sets a preference for a given user."""
    if not user_key:
        return
    if user_key not in _USER_PREFERENCES:
        _USER_PREFERENCES[user_key] = {}
    _USER_PREFERENCES[user_key][pref_key] = pref_value


def record_user_claim(
    asset_id: str,
    claim: str,
    reported_by: str,
    status: str = "unconfirmed",
    details: str = "",
) -> None:
    """Records a verbal or operator claim with provenance."""
    _CLAIMS.append(
        {
            "asset_id": asset_id,
            "claim": claim,
            "reported_by": reported_by,
            "status": status,
            "details": details,
        }
    )


def get_user_claims_for_asset(asset_id: str) -> list[dict[str, Any]]:
    """Returns all recorded user claims for an asset."""
    return [c for c in _CLAIMS if c.get("asset_id") == asset_id]
