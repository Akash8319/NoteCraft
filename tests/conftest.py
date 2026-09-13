"""
Pytest fixtures and mock objects for NoteCraft test suite.
"""

import io
import pytest
import pymupdf as fitz


@pytest.fixture
def sample_pdf_bytes():
    """Generates a small valid PDF in memory with known text content."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Lecture 3: CPU Scheduling Algorithms\n"
        "Operating Systems Concepts\n"
        "First-Come First-Served (FCFS): The process that requests the CPU first is allocated the CPU first.\n"
        "Shortest Job First (SJF): Associates each process with the length of its next CPU burst.\n"
        "Round Robin (RR): Designed especially for time-sharing systems using small units of CPU time called time quantum."
    )
    page.insert_text((50, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture
def empty_pdf_bytes():
    """Generates a PDF with empty pages (simulating blank or scanned slides without OCR)."""
    doc = fitz.open()
    doc.new_page()
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture
def sample_lecture_text():
    """Returns sample extracted lecture text."""
    return (
        "Operating Systems: CPU Scheduling Algorithms\n"
        "- FCFS (First-Come First-Served): Simple, non-preemptive. Can suffer from convoy effect.\n"
        "- SJF (Shortest Job First): Optimal average turnaround time, but requires burst prediction.\n"
        "- Round Robin: Preemptive, uses time quantum. Turnaround time depends heavily on quantum size."
    )


@pytest.fixture
def mock_gemini_raw_response():
    """Returns a realistic simulated Gemini model response with delimiter and quiz JSON."""
    return """## Executive Summary
CPU scheduling is the basis of multi-programmed operating systems. By switching the CPU among processes, the OS makes the computer more productive.

## Core Concepts & Definitions
- **Process State**: The current activity of a process including New, Ready, Running, Waiting, Terminated.
- **CPU Burst**: The cycle of CPU execution interspersed with I/O waits.
- **Preemptive Scheduling**: A process can be interrupted in the middle of execution and moved to ready state.

## Step-by-Step Mechanisms, Algorithms & Workflows
- **FCFS Algorithm**:
  1. Process arrives in ready queue.
  2. Dispatched in arrival order.
  3. Non-preemptive until completion or I/O.
- **Round Robin Algorithm**:
  1. Ready queue is treated as circular FIFO.
  2. CPU scheduler assigns time quantum (typically 10-100 ms).
  3. If burst > quantum, timer interrupt triggers context switch.

## Important Formulas, Syntax, or Rules
- **Turnaround Time**: `T_turnaround = T_completion - T_arrival`
- **Waiting Time**: `T_wait = T_turnaround - T_burst`

## High-Yield Exam Traps & Key Takeaways
- Convoy effect in FCFS causes lower CPU and device utilization.
- If Round Robin quantum is too large, it degenerates into FCFS.

===QUIZ_JSON===
[
  {
    "question": "What is the primary drawback of First-Come, First-Served (FCFS) scheduling?",
    "answer": "The convoy effect, where short processes get stuck waiting behind long CPU-bound processes.",
    "explanation": "FCFS is non-preemptive, leading to higher average waiting time when a long process monopolizes the CPU."
  },
  {
    "question": "How does time quantum size affect Round Robin scheduling performance?",
    "answer": "A very large quantum behaves like FCFS; a very small quantum causes excessive context-switching overhead.",
    "explanation": "Selecting the optimal quantum balances responsiveness with CPU utilization efficiency."
  },
  {
    "question": "Which scheduling algorithm produces the theoretically minimal average waiting time?",
    "answer": "Shortest Job First (SJF) / Shortest Remaining Time First (SRTF).",
    "explanation": "SJF is proven optimal by ordering shortest jobs first, though future burst lengths must be estimated."
  }
]
"""
