"""
Gemini API client wrapper for generating structured revision notes.
Keeps prompt construction and API error handling isolated from the UI layer.
"""

import json
import re
import time

from google import genai
from google.genai import types


class GeminiAPIError(Exception):
    """Raised when the Gemini API call fails or returns an unusable response."""
    pass


FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.7-flash",
]


SUBJECT_HINTS = {
    "General": "general academic content across any discipline",
    "Operating Systems": (
        "operating systems concepts (processes, threads, scheduling, memory "
        "management, concurrency, file systems, synchronization)"
    ),
    "Discrete Mathematics": (
        "discrete mathematics (set theory, logic, combinatorics, graph theory, "
        "proofs, relations, number theory)"
    ),
    "Java / C++": (
        "programming in Java or C++ (syntax, OOP concepts, memory management, "
        "standard library usage, common pitfalls)"
    ),
    "Data Structures & Algorithms": (
        "data structures and algorithms (complexity analysis, common patterns, "
        "trade-offs, pseudocode)"
    ),
    "Law": (
        "legal studies (statutes, case law, legal principles, definitions, "
        "precedents)"
    ),
    "Mathematics": "mathematics (theorems, derivations, formulas, proofs, problem-solving steps)",
    "Physics": "physics (laws, derivations, formulas, units, conceptual explanations)",
    "Business / Economics": "business or economics (frameworks, models, definitions, case concepts)",
}



QUIZ_DELIMITER = "===QUIZ_JSON==="


def build_prompt(extracted_text: str, subject: str, depth: str = "Comprehensive") -> str:
    subject_hint = SUBJECT_HINTS.get(subject, SUBJECT_HINTS["General"])

    prompt = f"""You are an elite academic professor, lead course instructor, and exam architect specializing in {subject_hint}.

A student has uploaded full lecture material. Your goal is to conduct an EXHAUSTIVE, IN-DEPTH, HIGH-YIELD ANALYSIS and synthesize structured, comprehensive master study notes.

CRITICAL INSTRUCTIONS:
1. DO NOT summarize aggressively or skip topics. Ensure COMPLETE, THOROUGH COVERAGE of ALL topics, modules, algorithms, definitions, states, metrics, mechanisms, and nuances present in the source material.
2. If there are processes, algorithms, or workflows (e.g. scheduling algorithms, memory mechanisms, mathematical methods, code syntax), explain each step-by-step, including their operational logic, advantages, disadvantages, and trade-offs.
3. Every key technical term must be explicitly defined and contextualized.
4. If there are formulas, equations, or calculation rules, provide the exact mathematical formula, define every variable, and describe how to solve problems with it.

Respond in exactly two parts, in this exact order, with nothing before or after them:

PART 1 — Markdown master notes with EXACTLY these five section headings (use "## Heading" syntax):

## Executive Summary
A comprehensive 2-3 paragraph academic synthesis. Clearly explain the overarching scope of this lecture material, the key architectural/theoretical goals, core problem statements addressed, and why this topic is vital for mastery and examinations.

## Core Concepts & Definitions
An exhaustive breakdown of ALL technical terms, components, structures, states, and concepts in the material.
Format EVERY entry strictly as a bullet point with a bold term:
* **Term**: Thorough, student-friendly definition followed by its functional role, importance, and practical context.
(Include as many terms as needed to cover the entire material thoroughly — do not leave out any concept mentioned in the lecture.)

## Step-by-Step Mechanisms, Algorithms & Workflows
Detailed, structured breakdown of all procedures, algorithms, workflows, transitions, lifecycle stages, or decision-making rules discussed in the lecture.
Use numbered steps, subheadings (###), comparison tables (using markdown tables where applicable), trade-offs, and concrete examples to explain how each system or method functions.

## Important Formulas, Syntax, or Rules
A dedicated compilation of ALL formulas, mathematical expressions, syntax structures, asymptotic complexities (Big-O), or formal laws.
For each formula/rule:
- State the formula clearly.
- Define each variable and constant.
- Explain when and how to apply it during exam problems or calculations.
(If genuinely no formulas or formal rules exist in this material, write "Not applicable to this material.")

## High-Yield Exam Traps & Key Takeaways
An extensive, high-impact bulleted list of:
- Critical distinctions and common student confusions or traps.
- Frequently tested edge cases, trade-offs (e.g. throughput vs latency, starvation vs fairness).
- High-probability examination questions and key recall points.

PART 2 — On a new line, write exactly this delimiter with nothing else on that line:
{QUIZ_DELIMITER}

Then, immediately after, a single valid JSON array (no markdown code fences, no commentary, just valid raw JSON) of exactly 5 high-yield exam practice questions testing true mastery (conceptual, analytical, and formula/mechanism scenarios):
[
  {{"question": "...", "answer": "...", "explanation": "..."}},
  ...
]

Tone: Rigorous, clear, academic, exam-focused, and thorough.

--- SOURCE MATERIAL START ---
{extracted_text}
--- SOURCE MATERIAL END ---
"""
    return prompt


def parse_notes_response(raw_text: str) -> dict:
    """
    Splits the model's raw output into structured sections and quiz items.
    Handles delimiters, variations in code fences, and arbitrary subheadings.
    """
    notes_part = raw_text
    quiz_part = ""

    if QUIZ_DELIMITER in raw_text:
        notes_part, quiz_part = raw_text.split(QUIZ_DELIMITER, 1)
    else:
        # Fallback: look for variations of QUIZ_DELIMITER with whitespace
        delim_match = re.search(r"={3,}\s*QUIZ_JSON\s*={3,}", raw_text, re.IGNORECASE)
        if delim_match:
            notes_part = raw_text[:delim_match.start()]
            quiz_part = raw_text[delim_match.end():]
        else:
            # Fallback: look for JSON array containing "question"
            json_pattern = re.search(r"(\[\s*\{\s*\"question\".*\}\s*\])", raw_text, re.DOTALL)
            if json_pattern:
                quiz_part = json_pattern.group(1)
                notes_part = raw_text[:json_pattern.start()]

    # Parse top-level "## Heading" (and "# Heading") blocks in order
    sections = {}
    heading_pattern = re.compile(r"^#{1,3}\s+([^#\n\r]+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(notes_part))

    if matches:
        for i, match in enumerate(matches):
            heading = match.group(1).strip()
            heading = re.sub(r"^\*\*|\*\*$", "", heading).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(notes_part)
            content = notes_part[start:end].strip()
            sections[heading] = content
    else:
        # Fallback if model didn't use ## format
        sections["Comprehensive Notes"] = notes_part.strip()

    # Parse quiz JSON tolerating stray code fences or extra whitespace
    quiz = []
    quiz_text = quiz_part.strip()
    quiz_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", quiz_text, flags=re.MULTILINE).strip()

    # Extract JSON array substring if needed
    array_match = re.search(r"(\[\s*\{.*\}\s*\])", quiz_text, re.DOTALL)
    if not array_match and raw_text:
        array_match = re.search(r"(\[\s*\{\s*\"question\".*\}\s*\])", raw_text, re.DOTALL)

    if array_match:
        quiz_json_str = array_match.group(1)
        cleaned_json = re.sub(r",\s*([\]}])", r"\1", quiz_json_str)
        try:
            parsed = json.loads(cleaned_json)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "question" in item and "answer" in item:
                        quiz.append({
                            "question": str(item.get("question", "")).strip(),
                            "answer": str(item.get("answer", "")).strip(),
                            "explanation": str(item.get("explanation", "")).strip(),
                        })
        except Exception:
            try:
                parsed = json.loads(quiz_json_str)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "question" in item and "answer" in item:
                            quiz.append({
                                "question": str(item.get("question", "")).strip(),
                                "answer": str(item.get("answer", "")).strip(),
                                "explanation": str(item.get("explanation", "")).strip(),
                            })
            except Exception:
                quiz = []

    return {"sections": sections, "quiz": quiz, "raw": raw_text}


def generate_revision_notes(
    api_key: str,
    extracted_text: str,
    subject: str,
    model_name: str = "gemini-3.5-flash-lite",
    depth: str = "Comprehensive",
    status_callback=None,
) -> dict:
    """
    Calls the Gemini API to generate structured revision notes with deep, comprehensive coverage.
    Includes multi-model fallback cascading and retry logic to gracefully bypass 503 UNAVAILABLE spikes.
    """
    if not api_key:
        raise GeminiAPIError(
            "No Gemini API key found. Add GEMINI_API_KEY to your .env file or "
            "Streamlit secrets before generating notes."
        )

    if not extracted_text or not extracted_text.strip():
        raise GeminiAPIError("There is no extracted text to send to the AI.")

    prompt = build_prompt(extracted_text, subject, depth=depth)
    client = genai.Client(api_key=api_key)

    # Ordered list of models to try if the primary encounters 503 high-demand or rate limits
    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_error = None

    for idx, target_model in enumerate(models_to_try):
        for attempt in range(2):
            try:
                if status_callback and idx > 0 and attempt == 0:
                    status_callback(f"🔄 High traffic detected on primary model. Switching to backup: {target_model}...")

                token_cap = 8192
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=token_cap,
                    ),
                )

                if not response or not getattr(response, "text", None):
                    raise GeminiAPIError(
                        "Gemini returned an empty response. This can happen if the "
                        "content was flagged by safety filters. Try a different PDF."
                    )

                # Check for truncation or incomplete generation
                cand = response.candidates[0] if getattr(response, "candidates", None) else None
                finish_reason = getattr(cand, "finish_reason", None)
                is_max_tokens = False
                if finish_reason is not None and "MAX_TOKENS" in str(finish_reason):
                    is_max_tokens = True

                parsed = parse_notes_response(response.text)
                is_incomplete = (len(parsed.get("quiz", [])) == 0 and len(parsed.get("sections", {})) <= 1)

                if is_max_tokens or is_incomplete:
                    raise GeminiAPIError(
                        f"Incomplete generation from {target_model} (finish_reason: {finish_reason}, sections: {len(parsed.get('sections', {}))}, quiz: {len(parsed.get('quiz', []))})."
                    )

                return parsed

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_transient = (
                    "503" in err_str
                    or "unavailable" in err_str
                    or "high demand" in err_str
                    or "429" in err_str
                    or "resource_exhausted" in err_str
                    or "quota" in err_str
                )
                if is_transient and attempt == 0:
                    time.sleep(1.5)
                    continue
                # If model is deprecated, truncated, or still 503/429, break out of attempt loop to try next fallback model
                break

    raise GeminiAPIError(
        f"All candidate Gemini models are currently experiencing temporary high demand or quota limits. "
        f"Spikes usually subside in a few seconds. Details: {last_error}"
    )



def ask_gemini_question(
    api_key: str,
    context_text: str,
    question: str,
    model_name: str = "gemini-3.5-flash-lite",
) -> str:
    """
    Allows a student to ask any follow-up question or clarification about their uploaded notes.
    Includes automated fallback across models if high demand (503) occurs.
    """
    if not api_key:
        raise GeminiAPIError("No Gemini API key found.")
    if not question or not question.strip():
        raise GeminiAPIError("Please provide a question.")

    prompt = f"""You are NoteCraft AI, an expert academic tutor and exam coach.
Below is the reference material extracted from the student's uploaded lecture:

--- REFERENCE MATERIAL START ---
{context_text[:14000]}
--- REFERENCE MATERIAL END ---

Student's Question:
{question}

Provide a clear, engaging, and accurate answer based primarily on the reference material above.
Use clean markdown formatting, bold keywords, and bullet points where helpful.
If the reference material does not contain the answer, clarify that and provide the standard academic explanation.
"""
    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_error = None
    client = genai.Client(api_key=api_key)

    for target_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1200,
                ),
            )
            if response and getattr(response, "text", None):
                return response.text.strip()
        except Exception as e:
            last_error = e
            continue

    raise GeminiAPIError(f"NoteCraft AI Tutor query failed: {last_error}")

