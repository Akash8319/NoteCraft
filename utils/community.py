"""
NoteCraft Study Community Module.
Powers collaborative study rooms, real-time group discussions,
shared revision vaults, and synchronized study sessions.
"""

from datetime import datetime
import uuid


DEFAULT_COMMUNITIES = [
    {
        "id": "comm-os",
        "name": "Operating Systems & Kernels",
        "icon": "💻",
        "description": "Deep-dive into process scheduling, virtual memory, paging algorithms, deadlock recovery, and kernel internals.",
        "category": "Computer Science",
        "tags": ["OS", "Memory", "Paging", "Deadlock", "Semaphores"],
        "active_topic": "Virtual Memory, TLB Misses & Page Fault Handling",
        "members": [
            {"name": "Dev Sharma", "email": "dev.sharma@gmail.com", "role": "Moderator"},
            {"name": "Priya Patel", "email": "priya.patel@gmail.com", "role": "Member"},
            {"name": "Rohan Das", "email": "rohan.das@gmail.com", "role": "Member"},
            {"name": "Ananya Gupta", "email": "ananya.gupta@gmail.com", "role": "Member"},
        ],
        "chat_messages": [
            {
                "id": "msg-os-1",
                "sender_name": "Dev Sharma",
                "sender_email": "dev.sharma@gmail.com",
                "sender_avatar": "https://ui-avatars.com/api/?name=Dev+Sharma&background=6366F1&color=ffffff&bold=true&rounded=true",
                "message": "Welcome everyone! Today we are prepping for the mid-sem OS exam. Drop your notes on page replacement (LRU vs Optimal) in the Shared Vault!",
                "timestamp": "Today at 08:30 PM",
                "is_question": False,
            },
            {
                "id": "msg-os-2",
                "sender_name": "Priya Patel",
                "sender_email": "priya.patel@gmail.com",
                "sender_avatar": "https://ui-avatars.com/api/?name=Priya+Patel&background=EC4899&color=ffffff&bold=true&rounded=true",
                "message": "Can someone clarify Belady's Anomaly? Does FIFO always guarantee more page faults when frame count increases, or only in certain cases?",
                "timestamp": "Today at 08:45 PM",
                "is_question": True,
            },
            {
                "id": "msg-os-3",
                "sender_name": "Rohan Das",
                "sender_email": "rohan.das@gmail.com",
                "sender_avatar": "https://ui-avatars.com/api/?name=Rohan+Das&background=10B981&color=ffffff&bold=true&rounded=true",
                "message": "Belady's anomaly occurs specifically with FIFO because it is not a stack algorithm! Algorithms like LRU and Optimal never suffer from it.",
                "timestamp": "Today at 08:52 PM",
                "is_question": False,
            },
        ],
        "shared_notes": [
            {
                "id": "sn-os-1",
                "title": "OS Paging & Virtual Memory Quick Cheat Sheet",
                "shared_by": "Dev Sharma",
                "shared_at": "Yesterday",
                "tags": ["Paging", "TLB", "Cheatsheet"],
                "content": (
                    "### Virtual Memory & Paging Core Formulas\n\n"
                    "- **Page Table Entry (PTE)** = Frame number + Control bits (Valid/Invalid, Dirty, Reference, Read/Write).\n"
                    "- **Effective Memory Access Time (EMAT)**:\n"
                    "  `EMAT = Hit_Ratio * (TLB_access + RAM_access) + (1 - Hit_Ratio) * (TLB_access + 2 * RAM_access)`\n"
                    "- **Inverted Page Table**: Maps frames to pages (one entry per physical frame) reducing table size dramatically.\n"
                    "- **Thrashing**: High paging activity where CPU utilization drops sharply as system spends more time servicing page faults than executing instructions."
                ),
            }
        ],
        "pomodoro": {
            "status": "studying",
            "duration_mins": 25,
            "session_topic": "OS Kernel & Page Replacement Sprint",
            "participants": 6,
        },
    },
    {
        "id": "comm-dsa",
        "name": "DSA Sprint & Problem Solving",
        "icon": "⚡",
        "description": "Daily LeetCode medium/hard breakdown, dynamic programming patterns, graphs, and Big-O trade-offs.",
        "category": "Algorithms",
        "tags": ["DSA", "LeetCode", "Dynamic Programming", "Graphs", "Trees"],
        "active_topic": "Graph Dijkstra vs Bellman-Ford & DP Knapsack Patterns",
        "members": [
            {"name": "Siddharth Rao", "email": "sid.rao@gmail.com", "role": "Moderator"},
            {"name": "Kavya Nair", "email": "kavya.nair@gmail.com", "role": "Member"},
            {"name": "Aman Verma", "email": "aman.verma@gmail.com", "role": "Member"},
        ],
        "chat_messages": [
            {
                "id": "msg-dsa-1",
                "sender_name": "Siddharth Rao",
                "sender_email": "sid.rao@gmail.com",
                "sender_avatar": "https://ui-avatars.com/api/?name=Siddharth+Rao&background=3B82F6&color=ffffff&bold=true&rounded=true",
                "message": "Today's daily challenge: Longest Common Subsequence using space optimization. Who solved it in O(min(N, M)) space?",
                "timestamp": "Today at 07:15 PM",
                "is_question": False,
            },
            {
                "id": "msg-dsa-2",
                "sender_name": "Kavya Nair",
                "sender_email": "kavya.nair@gmail.com",
                "sender_avatar": "https://ui-avatars.com/api/?name=Kavya+Nair&background=F59E0B&color=ffffff&bold=true&rounded=true",
                "message": "Just posted the two-row rolling DP array solution in the Shared Vault!",
                "timestamp": "Today at 07:28 PM",
                "is_question": False,
            },
        ],
        "shared_notes": [
            {
                "id": "sn-dsa-1",
                "title": "Mastering 14 LeetCode Patterns (Summary Deck)",
                "shared_by": "Siddharth Rao",
                "shared_at": "2 days ago",
                "tags": ["DP", "Sliding Window", "Two Pointers"],
                "content": (
                    "### Core Patterns Checklist:\n\n"
                    "1. **Two Pointers**: Sorted arrays, pair sums, palindrome verification.\n"
                    "2. **Sliding Window**: Subarray with max/min condition, longest substring without repeats.\n"
                    "3. **Fast & Slow Pointers**: Linked list cycle detection (Floyd's algorithm).\n"
                    "4. **Monotonic Stack**: Next Greater Element, Largest Rectangle in Histogram.\n"
                    "5. **0/1 Knapsack Pattern**: Iterate items, inner loop capacity backwards to prevent re-use."
                ),
            }
        ],
        "pomodoro": {
            "status": "idle",
            "duration_mins": 25,
            "session_topic": "Dynamic Programming Sprint",
            "participants": 3,
        },
    },
    {
        "id": "comm-math",
        "name": "Discrete Mathematics & Logic",
        "icon": "📐",
        "description": "Graph theory, predicate calculus, combinatorics, modular arithmetic, and recurrence relations.",
        "category": "Mathematics",
        "tags": ["Discrete Math", "Graph Theory", "Logic", "Combinatorics", "Proofs"],
        "active_topic": "Eulerian & Hamiltonian Paths, Master Theorem for Recurrences",
        "members": [
            {"name": "Prof. Alan Vance", "email": "alan.vance@gmail.com", "role": "Moderator"},
            {"name": "Neha Joshi", "email": "neha.joshi@gmail.com", "role": "Member"},
        ],
        "chat_messages": [
            {
                "id": "msg-math-1",
                "sender_name": "Neha Joshi",
                "sender_email": "neha.joshi@gmail.com",
                "sender_avatar": "https://ui-avatars.com/api/?name=Neha+Joshi&background=8B5CF6&color=ffffff&bold=true&rounded=true",
                "message": "Quick check: Does an undirected graph with exactly 2 odd-degree vertices always have an Eulerian path?",
                "timestamp": "Today at 06:10 PM",
                "is_question": True,
            },
            {
                "id": "msg-math-2",
                "sender_name": "Prof. Alan Vance",
                "sender_email": "alan.vance@gmail.com",
                "sender_avatar": "https://ui-avatars.com/api/?name=Alan+Vance&background=10B981&color=ffffff&bold=true&rounded=true",
                "message": "Yes! Provided all vertices with non-zero degree belong to a single connected component. The path starts at one odd vertex and ends at the other.",
                "timestamp": "Today at 06:22 PM",
                "is_question": False,
            },
        ],
        "shared_notes": [
            {
                "id": "sn-math-1",
                "title": "Master Theorem Quick Formula Card",
                "shared_by": "Prof. Alan Vance",
                "shared_at": "3 days ago",
                "tags": ["Master Theorem", "Recurrence", "Complexity"],
                "content": (
                    "### Master Theorem: `T(n) = aT(n/b) + f(n)`\n\n"
                    "Let `c = log_b(a)`:\n\n"
                    "- **Case 1**: If `f(n) = O(n^{c - ε})`, then `T(n) = Θ(n^c)`.\n"
                    "- **Case 2**: If `f(n) = Θ(n^c * log^k(n))`, then `T(n) = Θ(n^c * log^{k+1}(n))`.\n"
                    "- **Case 3**: If `f(n) = Ω(n^{c + ε})` and regularity holds, then `T(n) = Θ(f(n))`."
                ),
            }
        ],
        "pomodoro": {
            "status": "studying",
            "duration_mins": 30,
            "session_topic": "Graph Proofs & Logic Deep Work",
            "participants": 4,
        },
    },
    {
        "id": "comm-system",
        "name": "Full-Stack & System Design",
        "icon": "🌐",
        "description": "Scalable web architectures, database sharding, CAP theorem, WebSockets, and microservices.",
        "category": "Software Engineering",
        "tags": ["System Design", "Microservices", "Databases", "Caching", "Architecture"],
        "active_topic": "Distributed Caching with Redis & Rate Limiting Algorithms",
        "members": [
            {"name": "Karan Malhotra", "email": "karan.malhotra@gmail.com", "role": "Moderator"},
            {"name": "Sneha Roy", "email": "sneha.roy@gmail.com", "role": "Member"},
        ],
        "chat_messages": [
            {
                "id": "msg-sys-1",
                "sender_name": "Karan Malhotra",
                "sender_email": "karan.malhotra@gmail.com",
                "sender_avatar": "https://ui-avatars.com/api/?name=Karan+Malhotra&background=06B6D4&color=ffffff&bold=true&rounded=true",
                "message": "Remember for rate limiting in high-throughput APIs: Token Bucket vs Leaky Bucket vs Sliding Window Log. Which one handles bursts best?",
                "timestamp": "Today at 05:40 PM",
                "is_question": False,
            }
        ],
        "shared_notes": [],
        "pomodoro": {
            "status": "idle",
            "duration_mins": 25,
            "session_topic": "System Design Reading",
            "participants": 2,
        },
    },
]


def init_community_state(session_state) -> None:
    """Initializes the study communities list in Streamlit session state if not already set."""
    if "communities" not in session_state:
        # Deep copy default list
        import copy
        session_state["communities"] = copy.deepcopy(DEFAULT_COMMUNITIES)
    if "active_community_id" not in session_state:
        session_state["active_community_id"] = None
    if "group_search_query" not in session_state:
        session_state["group_search_query"] = ""


def get_all_communities(session_state) -> list[dict]:
    """Returns all available communities."""
    init_community_state(session_state)
    return session_state["communities"]


def get_community_by_id(session_state, comm_id: str) -> dict | None:
    """Finds a community by its ID."""
    init_community_state(session_state)
    for c in session_state["communities"]:
        if c["id"] == comm_id:
            return c
    return None


def is_user_member(community: dict, user_email: str) -> bool:
    """Checks if a user is currently a registered member of the community."""
    if not user_email:
        return False
    user_email_clean = user_email.strip().lower()
    return any(m.get("email", "").strip().lower() == user_email_clean for m in community.get("members", []))


def join_community(session_state, comm_id: str, user: dict) -> bool:
    """Adds an authenticated user to a community."""
    comm = get_community_by_id(session_state, comm_id)
    if not comm or not user:
        return False

    user_email = user.get("email", "").strip().lower()
    if not is_user_member(comm, user_email):
        comm["members"].append({
            "name": user.get("name", "Student"),
            "email": user_email,
            "avatar": user.get("avatar", ""),
            "role": "Member",
        })
        # Add automated welcome message
        comm["chat_messages"].append({
            "id": f"msg-join-{uuid.uuid4().hex[:6]}",
            "sender_name": "NoteCraft Bot",
            "sender_email": "bot@notecraft.ai",
            "sender_avatar": "https://ui-avatars.com/api/?name=NC+Bot&background=6366F1&color=ffffff&bold=true&rounded=true",
            "message": f"🎉 Welcome **{user.get('name', 'Student')}** to the study room! Let's study together.",
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "is_question": False,
        })
        return True
    return True


def leave_community(session_state, comm_id: str, user_email: str) -> bool:
    """Removes a user from a community."""
    comm = get_community_by_id(session_state, comm_id)
    if not comm or not user_email:
        return False

    clean_email = user_email.strip().lower()
    initial_len = len(comm["members"])
    comm["members"] = [m for m in comm["members"] if m.get("email", "").strip().lower() != clean_email]
    return len(comm["members"]) < initial_len


def create_community(
    session_state,
    name: str,
    description: str,
    category: str,
    icon: str = "📚",
    creator_user: dict = None,
    tags: list = None,
) -> dict:
    """Creates a new study community and adds creator as moderator."""
    init_community_state(session_state)
    new_id = f"comm-{uuid.uuid4().hex[:6]}"
    members = []
    if creator_user:
        members.append({
            "name": creator_user.get("name", "Organizer"),
            "email": creator_user.get("email", "").strip().lower(),
            "avatar": creator_user.get("avatar", ""),
            "role": "Moderator",
        })

    new_comm = {
        "id": new_id,
        "name": name.strip(),
        "icon": icon.strip() or "📚",
        "description": description.strip(),
        "category": category.strip() or "General Study",
        "tags": tags or ["Study", "Exam Prep"],
        "active_topic": f"Intro to {name.strip()}",
        "members": members,
        "chat_messages": [
            {
                "id": f"msg-init-{new_id}",
                "sender_name": "NoteCraft Bot",
                "sender_email": "bot@notecraft.ai",
                "sender_avatar": "https://ui-avatars.com/api/?name=NC+Bot&background=6366F1&color=ffffff&bold=true&rounded=true",
                "message": f"✨ Welcome to **{name.strip()}**! Start by sharing questions, notes, or kicking off a Pomodoro study session.",
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "is_question": False,
            }
        ],
        "shared_notes": [],
        "pomodoro": {
            "status": "idle",
            "duration_mins": 25,
            "session_topic": f"{name.strip()} Focus",
            "participants": 1 if creator_user else 0,
        },
    }
    session_state["communities"].insert(0, new_comm)
    return new_comm


def post_chat_message(
    session_state,
    comm_id: str,
    user: dict,
    message: str,
    is_question: bool = False,
) -> dict | None:
    """Posts a chat message to a community."""
    comm = get_community_by_id(session_state, comm_id)
    if not comm or not message or not message.strip():
        return None

    msg_obj = {
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "sender_name": user.get("name", "Anonymous"),
        "sender_email": user.get("email", ""),
        "sender_avatar": user.get(
            "avatar",
            f"https://ui-avatars.com/api/?name={user.get('name', 'User')}&background=6366F1&color=ffffff&rounded=true",
        ),
        "message": message.strip(),
        "timestamp": datetime.now().strftime("%I:%M %p"),
        "is_question": is_question,
    }
    comm["chat_messages"].append(msg_obj)
    return msg_obj


def share_notes_deck(
    session_state,
    comm_id: str,
    user: dict,
    title: str,
    content: str,
    tags: list = None,
) -> dict | None:
    """Shares a revision notes deck to a community's shared notes vault."""
    comm = get_community_by_id(session_state, comm_id)
    if not comm or not content:
        return None

    deck_obj = {
        "id": f"sn-{uuid.uuid4().hex[:6]}",
        "title": title.strip() or "Untitled Revision Notes",
        "shared_by": user.get("name", "Fellow Student"),
        "shared_at": datetime.now().strftime("%b %d, %I:%M %p"),
        "tags": tags or ["Revision", "Notes"],
        "content": content,
    }
    comm["shared_notes"].insert(0, deck_obj)
    return deck_obj
