"""
Unit tests for NoteCraft Community module (utils/community.py).
Tests community initialization, group creation, member joins, chat feed, and notes sharing.
"""

from utils.community import (
    init_community_state,
    get_all_communities,
    get_community_by_id,
    is_user_member,
    join_community,
    leave_community,
    create_community,
    post_chat_message,
    share_notes_deck,
)


def test_community_init():
    session = {}
    init_community_state(session)
    assert "communities" in session
    assert len(session["communities"]) >= 4

    os_comm = get_community_by_id(session, "comm-os")
    assert os_comm is not None
    assert "Operating Systems" in os_comm["name"]


def test_join_and_leave_community():
    session = {}
    init_community_state(session)
    user = {
        "name": "Test Student",
        "email": "student.test@gmail.com",
        "avatar": "https://ui-avatars.com/api/?name=Test+Student",
    }

    comm = get_community_by_id(session, "comm-dsa")
    assert not is_user_member(comm, user["email"])

    # Join
    joined = join_community(session, "comm-dsa", user)
    assert joined is True
    assert is_user_member(comm, user["email"])

    # Double join should be idempotent
    joined_again = join_community(session, "comm-dsa", user)
    assert joined_again is True

    # Leave
    left = leave_community(session, "comm-dsa", user["email"])
    assert left is True
    assert not is_user_member(comm, user["email"])


def test_create_community():
    session = {}
    init_community_state(session)
    creator = {
        "name": "Prof Alan",
        "email": "alan@stanford.edu",
        "avatar": "https://ui-avatars.com/api/?name=Alan",
    }

    new_comm = create_community(
        session,
        name="Quantum Computing 101",
        description="Qubits, superposition, and Shor's algorithm.",
        category="Physics / CS",
        icon="⚛️",
        creator_user=creator,
        tags=["Quantum", "Physics", "Algorithms"],
    )

    assert new_comm["id"].startswith("comm-")
    assert new_comm["name"] == "Quantum Computing 101"
    assert is_user_member(new_comm, creator["email"])
    assert len(session["communities"]) > 4


def test_post_chat_message():
    session = {}
    init_community_state(session)
    user = {"name": "Akash Gautam", "email": "akash@gmail.com"}

    # Post normal message
    msg = post_chat_message(session, "comm-os", user, "Hello study group!")
    assert msg is not None
    assert msg["message"] == "Hello study group!"
    assert msg["sender_name"] == "Akash Gautam"
    assert msg["is_question"] is False

    # Post question
    q_msg = post_chat_message(
        session,
        "comm-os",
        user,
        "What is the difference between soft and hard real-time systems?",
        is_question=True,
    )
    assert q_msg is not None
    assert q_msg["is_question"] is True


def test_share_notes_deck():
    session = {}
    init_community_state(session)
    user = {"name": "Akash Gautam", "email": "akash@gmail.com"}

    deck = share_notes_deck(
        session,
        "comm-os",
        user,
        title="Deadlock Prevention Cheat Sheet",
        content="### Deadlock 4 Conditions: Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait.",
        tags=["Deadlock", "OS"],
    )

    assert deck is not None
    assert deck["title"] == "Deadlock Prevention Cheat Sheet"
    os_comm = get_community_by_id(session, "comm-os")
    assert any(d["id"] == deck["id"] for d in os_comm["shared_notes"])
