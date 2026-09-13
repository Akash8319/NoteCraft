"""
Unit tests for utils/gemini_client.py.
Validates prompt formatting, response parsing, error handling, 503 fallback cascading, and quiz extraction.
"""

from unittest.mock import MagicMock, patch
import pytest

from utils.gemini_client import (
    build_prompt,
    parse_notes_response,
    generate_revision_notes,
    ask_gemini_question,
    GeminiAPIError,
    SUBJECT_HINTS,
    FALLBACK_MODELS,
    QUIZ_DELIMITER,
)


def test_subject_hints_coverage():
    """Ensures major academic disciplines have tailored system hints."""
    expected_subjects = [
        "General",
        "Operating Systems",
        "Discrete Mathematics",
        "Java / C++",
        "Data Structures & Algorithms",
        "Law",
        "Mathematics",
        "Physics",
        "Business / Economics",
    ]
    for subj in expected_subjects:
        assert subj in SUBJECT_HINTS
        assert len(SUBJECT_HINTS[subj]) > 10


def test_build_prompt_includes_subject_and_depth(sample_lecture_text):
    """Verifies that custom prompts include subject context, depth, and the source text."""
    prompt = build_prompt(sample_lecture_text, subject="Operating Systems", depth="Exhaustive")
    assert "operating systems concepts" in prompt.lower()
    assert sample_lecture_text in prompt
    assert QUIZ_DELIMITER in prompt
    assert "PART 2" in prompt


def test_parse_notes_response_valid(mock_gemini_raw_response):
    """Verifies clean extraction of markdown sections and structured quiz items."""
    parsed = parse_notes_response(mock_gemini_raw_response)
    sections = parsed["sections"]
    quiz = parsed["quiz"]

    assert "Executive Summary" in sections
    assert "Core Concepts & Definitions" in sections
    assert "Step-by-Step Mechanisms, Algorithms & Workflows" in sections
    assert "Important Formulas, Syntax, or Rules" in sections
    assert "High-Yield Exam Traps & Key Takeaways" in sections

    assert len(quiz) == 3
    for q in quiz:
        assert "question" in q and len(q["question"]) > 5
        assert "answer" in q and len(q["answer"]) > 5
        assert "explanation" in q


def test_parse_notes_response_tolerates_markdown_code_fence():
    """Verifies parser tolerates ```json and ``` code fences surrounding the quiz JSON."""
    raw = f"""## Executive Summary
Test summary content.

{QUIZ_DELIMITER}
```json
[
  {{"question": "What is P1?", "answer": "Answer 1", "explanation": "Expl 1"}}
]
```
"""
    parsed = parse_notes_response(raw)
    assert "Executive Summary" in parsed["sections"]
    assert len(parsed["quiz"]) == 1
    assert parsed["quiz"][0]["question"] == "What is P1?"


def test_parse_notes_response_missing_delimiter_fallback():
    """Verifies fallback parsing when the model omits the delimiter but includes JSON."""
    raw = """## Core Concepts
Definitions here.

[
  {"question": "Fallback question?", "answer": "Fallback answer.", "explanation": "Fallback explanation."}
]
"""
    parsed = parse_notes_response(raw)
    assert "Core Concepts" in parsed["sections"]
    assert len(parsed["quiz"]) == 1
    assert parsed["quiz"][0]["question"] == "Fallback question?"


def test_generate_revision_notes_missing_api_key():
    """Verifies that missing API keys raise a descriptive GeminiAPIError."""
    with pytest.raises(GeminiAPIError, match="No Gemini API key found"):
        generate_revision_notes(api_key="", extracted_text="Some text", subject="General")


def test_generate_revision_notes_empty_text():
    """Verifies that empty extracted text raises a descriptive GeminiAPIError."""
    with pytest.raises(GeminiAPIError, match="no extracted text"):
        generate_revision_notes(api_key="mock_key_123", extracted_text="   ", subject="General")


@patch("utils.gemini_client.genai.Client")
def test_generate_revision_notes_success_mock(mock_client_cls, mock_gemini_raw_response):
    """Verifies end-to-end execution of generate_revision_notes using mocked client."""
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_gemini_raw_response
    mock_instance.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_instance

    result = generate_revision_notes(
        api_key="test_api_key",
        extracted_text="Operating systems lecture text",
        subject="Operating Systems",
    )
    assert "sections" in result
    assert "quiz" in result
    assert len(result["quiz"]) == 3
    assert mock_instance.models.generate_content.called


@patch("utils.gemini_client.genai.Client")
def test_generate_revision_notes_503_fallback_cascade(mock_client_cls, mock_gemini_raw_response):
    """
    CRITICAL TEST: Verifies that when the primary model encounters a 503 UNAVAILABLE
    traffic spike, the system automatically catches it and seamlessly falls back to the
    next model in the cascade!
    """
    mock_instance = MagicMock()
    mock_success_response = MagicMock()
    mock_success_response.text = mock_gemini_raw_response

    # First call on primary throws 503; second call on fallback succeeds
    call_count = [0]
    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if kwargs.get("model") == "gemini-3.6-flash":
            raise Exception("503 UNAVAILABLE: This model is currently experiencing high demand.")
        return mock_success_response

    mock_instance.models.generate_content.side_effect = side_effect
    mock_client_cls.return_value = mock_instance

    status_messages = []
    result = generate_revision_notes(
        api_key="test_api_key",
        extracted_text="Operating systems lecture text",
        subject="Operating Systems",
        model_name="gemini-3.6-flash",
        status_callback=lambda msg: status_messages.append(msg),
    )

    assert "sections" in result
    assert len(result["quiz"]) == 3
    # Verify fallback was triggered
    assert len(status_messages) > 0
    assert "switching to backup" in status_messages[0].lower()


@patch("utils.gemini_client.genai.Client")
def test_ask_gemini_question_success(mock_client_cls):
    """Verifies that ask_gemini_question returns clean tutor advice."""
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "A process is an active program with a program counter and resources."
    mock_instance.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_instance

    answer = ask_gemini_question(
        api_key="test_key",
        context_text="OS context",
        question="What is a process?",
    )
    assert "process" in answer.lower()


@patch("utils.gemini_client.genai.Client")
def test_generate_revision_notes_incomplete_fallback_cascade(mock_client_cls, mock_gemini_raw_response):
    """Verifies that when a candidate output is truncated (0 quiz, 1 section), fallback model is invoked."""
    mock_instance = MagicMock()
    mock_truncated = MagicMock()
    mock_truncated.text = "Incomplete notes without headings or quiz delimiter"
    mock_truncated.candidates = [MagicMock(finish_reason="FinishReason.MAX_TOKENS")]

    mock_success = MagicMock()
    mock_success.text = mock_gemini_raw_response
    mock_success.candidates = [MagicMock(finish_reason="FinishReason.STOP")]

    call_count = [0]
    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_truncated
        return mock_success

    mock_instance.models.generate_content.side_effect = side_effect
    mock_client_cls.return_value = mock_instance

    status_messages = []
    result = generate_revision_notes(
        api_key="test_api_key",
        extracted_text="Operating systems lecture text",
        subject="Operating Systems",
        status_callback=lambda msg: status_messages.append(msg),
    )

    assert "sections" in result
    assert len(result["quiz"]) == 3
    assert len(status_messages) > 0

