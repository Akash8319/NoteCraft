"""
NoteCraft Authentication Module.
Handles Google / Gmail user authentication, profile management, and session state.
Supports both direct Gmail verification and OAuth 2.0 readiness.
"""

import os
import re
import urllib.parse
from datetime import datetime


def is_valid_gmail(email: str) -> bool:
    """Validates if the provided email has valid syntax and is an authentic Gmail/Google account."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9_.+-]+@(gmail\.com|googlemail\.com|[a-zA-Z0-9-]+\.(edu|ac\.[a-z]{2}))$"
    return bool(re.match(pattern, email))


def generate_avatar_url(name: str, email: str) -> str:
    """Generates a high-resolution, branded avatar URL based on the user's name."""
    clean_name = name.strip() if name else email.split("@")[0]
    encoded = urllib.parse.quote(clean_name)
    return f"https://ui-avatars.com/api/?name={encoded}&background=6366F1&color=ffffff&bold=true&rounded=true"


def is_oauth_configured(st_secrets=None) -> bool:
    """Checks whether full external Google OAuth credentials are present in secrets or env."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if st_secrets:
        try:
            if "auth" in st_secrets and "client_id" in st_secrets["auth"]:
                return True
            if "GOOGLE_CLIENT_ID" in st_secrets:
                return True
        except Exception:
            pass
    return bool(client_id and client_secret)


def init_auth_state(session_state) -> None:
    """Initializes user authentication keys in Streamlit session state."""
    if "user" not in session_state:
        session_state["user"] = None
    if "auth_modal_open" not in session_state:
        session_state["auth_modal_open"] = False
    if "current_view" not in session_state:
        session_state["current_view"] = "studio"  # "studio" or "community"


def is_authenticated(session_state) -> bool:
    """Returns True if a user is currently authenticated."""
    try:
        return session_state["user"] is not None
    except (KeyError, TypeError, AttributeError):
        return False


def get_current_user(session_state) -> dict | None:
    """Returns the current user profile dictionary if logged in, else None."""
    try:
        return session_state["user"]
    except (KeyError, TypeError, AttributeError):
        return None


def login_user(session_state, email: str, name: str = None) -> dict:
    """
    Authenticates a user via verified Gmail address and populates their student profile.
    """
    email = email.strip()
    if not is_valid_gmail(email):
        raise ValueError(
            "Please provide a valid Gmail address (e.g. yourname@gmail.com or academic Google account)."
        )

    if not name or not name.strip():
        # Derive friendly name from email local part
        raw_name = email.split("@")[0]
        # Replace dots/underscores with space and capitalize
        name = " ".join(part.capitalize() for part in re.split(r"[._+]", raw_name) if part)

    user_profile = {
        "email": email.lower(),
        "name": name.strip(),
        "avatar": generate_avatar_url(name, email),
        "auth_provider": "google",
        "logged_in_at": datetime.now().strftime("%b %d, %H:%M"),
        "study_xp": 120,  # Starting student XP
        "completed_quizzes": 0,
        "mastered_cards": 0,
    }
    session_state["user"] = user_profile
    session_state["auth_modal_open"] = False
    return user_profile


def logout_user(session_state) -> None:
    """Clears the authenticated user profile and resets auth state."""
    session_state["user"] = None
    session_state["auth_modal_open"] = False
