"""
End-to-End Integration test for NoteCraft Studio and Community Hub.
Uses streamlit.testing.v1.AppTest to simulate interactive user journeys.
"""

from streamlit.testing.v1 import AppTest
from utils.auth import login_user, get_current_user, is_authenticated
from utils.community import (
    get_all_communities,
    get_community_by_id,
    join_community,
    post_chat_message,
    share_notes_deck,
)


def test_app_initial_render():
    """Verifies that app.py loads cleanly with defaults."""
    at = AppTest.from_file("../app.py").run(timeout=10)
    assert not at.exception
    assert at.session_state["dark_mode"] is True
    assert at.session_state["current_view"] == "studio"


def test_app_community_navigation_and_auth_flow():
    """Simulates user logging in with Gmail, switching to Community Hub, and interacting with study groups."""
    at = AppTest.from_file("../app.py").run(timeout=10)
    assert not at.exception

    # 1. Simulate user signing in with Gmail
    user = login_user(at.session_state, "akash.gautam@gmail.com", "Akash Kumar Gautam")
    assert is_authenticated(at.session_state)
    assert user["email"] == "akash.gautam@gmail.com"

    # 2. Switch view to Community Hub
    at.session_state["current_view"] = "community"
    at.run(timeout=10)
    assert not at.exception

    # 3. Enter Operating Systems room
    at.session_state["active_community_id"] = "comm-os"
    at.run(timeout=10)
    assert not at.exception

    # 4. Post a question
    comm = get_community_by_id(at.session_state, "comm-os")
    assert comm is not None
    msg = post_chat_message(
        at.session_state,
        "comm-os",
        user,
        "Can someone explain TLB reach and multilevel paging?",
        is_question=True,
    )
    assert msg["is_question"] is True
    assert any(m["id"] == msg["id"] for m in comm["chat_messages"])

    # 5. Share notes deck into the group
    deck = share_notes_deck(
        at.session_state,
        "comm-os",
        user,
        title="Virtual Memory & TLB Quick Sheet",
        content="### TLB hit vs miss formulas\nEMAT calculation rules.",
        tags=["OS", "TLB", "Cheatsheet"],
    )
    assert deck["title"] == "Virtual Memory & TLB Quick Sheet"
    assert any(d["id"] == deck["id"] for d in comm["shared_notes"])

    # 6. Re-run app with updated room state
    at.run(timeout=10)
    assert not at.exception
