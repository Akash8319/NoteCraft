"""
Unit tests for NoteCraft app logic, state handling, flashcard extraction, and video topic curation.
"""

from app import (
    extract_flashcards_from_result,
    extract_video_topics,
    SECTION_ICONS,
    SUBJECT_ICONS,
)


def test_extract_flashcards_from_result(mock_gemini_raw_response):
    """Verifies that flashcards are parsed cleanly from bold terms in sections."""
    from utils.gemini_client import parse_notes_response
    parsed = parse_notes_response(mock_gemini_raw_response)
    flashcards = extract_flashcards_from_result(parsed)

    assert len(flashcards) >= 3
    terms = [fc["term"] for fc in flashcards]
    assert any("Process State" in t for t in terms)
    assert any("CPU Burst" in t for t in terms)


def test_extract_flashcards_fallback_to_quiz():
    """Verifies that when bullet terms are few, quiz questions are added as flashcards."""
    scant_result = {
        "sections": {
            "Core Concepts & Definitions": "- **Process**: Running program."
        },
        "quiz": [
            {"question": "What is starvation?", "answer": "Indefinite delay.", "explanation": "Low priority."}
        ]
    }
    cards = extract_flashcards_from_result(scant_result)
    assert len(cards) >= 2
    terms = [c["term"] for c in cards]
    assert "Process" in terms
    assert "What is starvation?" in terms


def test_extract_video_topics_from_subheadings():
    """Verifies that video topics are correctly extracted from ### markdown subheadings."""
    sample_result = {
        "sections": {
            "Step-by-Step Mechanisms, Algorithms & Workflows": (
                "### Round Robin Scheduling Algorithm\nDetails...\n"
                "### Shortest Remaining Time First (SRTF)\nDetails...\n"
            ),
            "Core Concepts & Definitions": "- **Context Switch**: Saving state.\n"
        },
        "meta": {"subject": "Operating Systems", "base_name": "OS_Lecture3"}
    }
    topics = extract_video_topics(sample_result)
    assert len(topics) >= 3
    assert "Round Robin Scheduling Algorithm" in topics
    assert "Shortest Remaining Time First (SRTF)" in topics
    assert "Context Switch" in topics


def test_extract_video_topics_fallback():
    """Verifies graceful fallback topics when no headings or terms exist."""
    empty_result = {
        "sections": {},
        "meta": {"subject": "Operating Systems", "base_name": "OS_Unit_1"}
    }
    topics = extract_video_topics(empty_result)
    assert len(topics) >= 1
    assert "OS Unit 1" in topics[0]


def test_section_and_subject_icons():
    """Verifies all mandatory sections and subjects have defined iconography."""
    assert "Executive Summary" in SECTION_ICONS
    assert "Core Concepts & Definitions" in SECTION_ICONS
    assert "Step-by-Step Mechanisms, Algorithms & Workflows" in SECTION_ICONS
    assert "Operating Systems" in SUBJECT_ICONS
    assert "Discrete Mathematics" in SUBJECT_ICONS


def test_extract_flashcards_from_numbered_and_inline_bold():
    """Verifies that numbered lists and inline bold definitions are captured as flashcards."""
    result = {
        "sections": {
            "Step-by-Step Mechanisms, Algorithms & Workflows": (
                "1. **Arrival Time**: When process enters ready queue.\n"
                "2. **Burst Time**: CPU execution duration.\n"
                "In addition, **Turnaround Time**: Total elapsed time from submission to completion.\n"
            )
        },
        "quiz": []
    }
    cards = extract_flashcards_from_result(result)
    assert len(cards) == 3
    terms = [c["term"] for c in cards]
    assert "Arrival Time" in terms
    assert "Burst Time" in terms
    assert "Turnaround Time" in terms

