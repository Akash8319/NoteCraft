"""
Unit tests for NoteCraft Authentication module (utils/auth.py).
Tests Gmail validation, avatar generation, user login, logout, and session state.
"""

import pytest
from utils.auth import (
    is_valid_gmail,
    generate_avatar_url,
    init_auth_state,
    is_authenticated,
    get_current_user,
    login_user,
    logout_user,
    is_oauth_configured,
)


def test_is_valid_gmail_standard():
    assert is_valid_gmail("student@gmail.com") is True
    assert is_valid_gmail("john.doe+study@gmail.com") is True
    assert is_valid_gmail("scholar@googlemail.com") is True


def test_is_valid_gmail_academic():
    assert is_valid_gmail("student@stanford.edu") is True
    assert is_valid_gmail("researcher@oxford.ac.uk") is True
    assert is_valid_gmail("akash@vitbhopal.ac.in") is True


def test_is_valid_gmail_invalid():
    assert is_valid_gmail("notanemail") is False
    assert is_valid_gmail("user@yahoo.com") is False
    assert is_valid_gmail("user@hotmail.com") is False
    assert is_valid_gmail("") is False
    assert is_valid_gmail(None) is False


def test_generate_avatar_url():
    url = generate_avatar_url("Akash Gautam", "akash@gmail.com")
    assert "ui-avatars.com" in url
    assert "Akash%20Gautam" in url or "Akash+Gautam" in url

    url2 = generate_avatar_url("", "priya@gmail.com")
    assert "priya" in url2


def test_auth_lifecycle():
    fake_session = {}
    init_auth_state(fake_session)
    assert fake_session["user"] is None
    assert is_authenticated(fake_session) is False
    assert get_current_user(fake_session) is None

    # Login with valid email & custom name
    profile = login_user(fake_session, "akash.gautam@gmail.com", name="Akash Kumar Gautam")
    assert profile["email"] == "akash.gautam@gmail.com"
    assert profile["name"] == "Akash Kumar Gautam"
    assert profile["auth_provider"] == "google"
    assert is_authenticated(fake_session) is True
    assert get_current_user(fake_session) == profile

    # Logout
    logout_user(fake_session)
    assert fake_session["user"] is None
    assert is_authenticated(fake_session) is False


def test_login_name_derivation():
    fake_session = {}
    profile = login_user(fake_session, "priya.patel.vit@gmail.com")
    assert profile["name"] == "Priya Patel Vit"


def test_login_invalid_email_raises():
    fake_session = {}
    with pytest.raises(ValueError, match="valid Gmail address"):
        login_user(fake_session, "hacker@randominvaliddomain.xyz")


def test_is_oauth_configured():
    # Without env vars
    assert isinstance(is_oauth_configured({}), bool)
