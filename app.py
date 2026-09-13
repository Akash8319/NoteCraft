"""
NoteCraft AI
------------
Single-flow app: Lecture PDF -> structured revision notes + flashcards + interactive quiz + AI tutor.

Built for: Prompt Wars Hackathon (Google for Developers x Hack2Skill x Android Club, VIT Bhopal)
Problem statement: AI-Powered Student Workspace (Flow: Lecture PDF -> revision notes)
"""

import os
import re
import json
import time
import html
import hashlib
import urllib.parse
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from utils.pdf_extractor import extract_text_from_pdf
from utils.gemini_client import (
    generate_revision_notes,
    ask_gemini_question,
    GeminiAPIError,
    SUBJECT_HINTS,
)
from utils.auth import (
    init_auth_state,
    is_authenticated,
    get_current_user,
    login_user,
    logout_user,
    is_valid_gmail,
    generate_avatar_url,
)
from utils.community import (
    init_community_state,
    get_all_communities,
    get_community_by_id,
    join_community,
    leave_community,
    create_community,
    post_chat_message,
    share_notes_deck,
    is_user_member,
)

load_dotenv()

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="NoteCraft | AI Academic Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Session defaults
# --------------------------------------------------------------------------
init_auth_state(st.session_state)
init_community_state(st.session_state)

if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = True
if "history" not in st.session_state:
    st.session_state["history"] = []
if "result" not in st.session_state:
    st.session_state["result"] = None
if "quiz_feedback" not in st.session_state:
    st.session_state["quiz_feedback"] = {}
if "flashcard_idx" not in st.session_state:
    st.session_state["flashcard_idx"] = 0
if "flashcard_flipped" not in st.session_state:
    st.session_state["flashcard_flipped"] = False
if "flashcards_mastered" not in st.session_state:
    st.session_state["flashcards_mastered"] = set()
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "concept_search_query" not in st.session_state:
    st.session_state["concept_search_query"] = ""

# --------------------------------------------------------------------------
# Theme tokens & Global Design System
# --------------------------------------------------------------------------
LIGHT_TOKENS = {
    "bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "surface-alt": "#F1F5F9",
    "surface-card": "#FFFFFF",
    "border": "#E2E8F0",
    "border-hover": "#CBD5E1",
    "text-primary": "#0F172A",
    "text-secondary": "#475569",
    "text-muted": "#94A3B8",
    "primary": "#4F46E5",
    "primary-hover": "#4338CA",
    "primary-gradient": "linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #06B6D4 100%)",
    "primary-glow": "rgba(79, 70, 229, 0.18)",
    "indigo": "#4F46E5",
    "violet": "#7C3AED",
    "cyan": "#0891B2",
    "emerald": "#059669",
    "amber-bg": "#FFFBEB",
    "amber-border": "#FCD34D",
    "amber-text": "#92400E",
    "card-shadow": "0 4px 20px -2px rgba(15, 23, 42, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.04)",
    "card-hover-shadow": "0 12px 30px -4px rgba(79, 70, 229, 0.12), 0 4px 10px -2px rgba(15, 23, 42, 0.06)",
    "hero-bg": "linear-gradient(135deg, rgba(79, 70, 229, 0.06) 0%, rgba(124, 58, 237, 0.06) 50%, rgba(6, 182, 212, 0.04) 100%)",
}

DARK_TOKENS = {
    "bg": "#0B0E17",
    "surface": "#131826",
    "surface-alt": "#1A2133",
    "surface-card": "#151B2B",
    "border": "rgba(255, 255, 255, 0.08)",
    "border-hover": "rgba(255, 255, 255, 0.16)",
    "text-primary": "#F8FAFC",
    "text-secondary": "#94A3B8",
    "text-muted": "#64748B",
    "primary": "#6366F1",
    "primary-hover": "#818CF8",
    "primary-gradient": "linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #06B6D4 100%)",
    "primary-glow": "rgba(99, 102, 241, 0.28)",
    "indigo": "#818CF8",
    "violet": "#A78BFA",
    "cyan": "#22D3EE",
    "emerald": "#34D399",
    "amber-bg": "rgba(245, 158, 11, 0.08)",
    "amber-border": "rgba(245, 158, 11, 0.28)",
    "amber-text": "#FBBF24",
    "card-shadow": "0 8px 32px 0 rgba(0, 0, 0, 0.36)",
    "card-hover-shadow": "0 14px 40px 0 rgba(99, 102, 241, 0.2)",
    "hero-bg": "linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.1) 50%, rgba(6, 182, 212, 0.06) 100%)",
}

TOKENS = DARK_TOKENS if st.session_state["dark_mode"] else LIGHT_TOKENS
root_vars = "\n".join(f"--{k}: {v};" for k, v in TOKENS.items())

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
    --radius-sm: 8px;
    --radius: 14px;
    --radius-lg: 22px;
    {root_vars}
}}

/* Base & Typography */
html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}

/* Accessibility & Keyboard Focus (WCAG 2.1 AA) */
:focus-visible {{
    outline: 2px solid var(--primary) !important;
    outline-offset: 2px !important;
}}

@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }}
}}

/* Custom Sleek Scrollbar */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
::-webkit-scrollbar-track {{
    background: transparent;
}}
::-webkit-scrollbar-thumb {{
    background: rgba(148, 163, 184, 0.25);
    border-radius: 999px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: rgba(99, 102, 241, 0.6);
}}

/* Ambient Background with Cyber Tech Grid & Multi-radial Glow */
.stApp {{
    background-color: var(--bg);
    background-image: 
        radial-gradient(circle at 12% 12%, rgba(99, 102, 241, 0.12) 0%, transparent 45%),
        radial-gradient(circle at 88% 88%, rgba(139, 92, 246, 0.10) 0%, transparent 45%),
        radial-gradient(circle at 50% 25%, rgba(6, 182, 212, 0.08) 0%, transparent 40%),
        radial-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 100% 100%, 28px 28px;
    background-attachment: fixed;
}}

/* Header & Top Bar Optimization */
header[data-testid="stHeader"] {{
    background-color: transparent !important;
    height: 1.8rem !important;
}}

.stDeployButton {{
    display: none !important;
}}

.block-container {{
    padding-top: 0.3rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1160px;
}}

/* Global Top Navigation Bar */
.top-nav-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    background: var(--surface-card);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 999px;
    padding: 8px 22px;
    margin-bottom: 14px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(20px) saturate(160%);
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}}

.top-nav-bar:hover {{
    border-color: rgba(99, 102, 241, 0.35);
    box-shadow: 0 10px 36px 0 rgba(99, 102, 241, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.16);
}}

.top-nav-left {{
    display: flex;
    align-items: center;
    gap: 10px;
}}

.live-dot-pulse {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--emerald);
    box-shadow: 0 0 0 rgba(52, 211, 153, 0.6);
    animation: pulseDot 2s infinite cubic-bezier(0.4, 0, 0.6, 1);
}}

@keyframes pulseDot {{
    0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7); }}
    70% {{ transform: scale(1); box-shadow: 0 0 0 7px rgba(52, 211, 153, 0); }}
    100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }}
}}

.top-nav-brand {{
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 0.88rem;
    color: var(--text-primary);
    letter-spacing: -0.01em;
}}

.top-nav-version {{
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(99, 102, 241, 0.15);
    color: var(--indigo);
    border: 1px solid rgba(99, 102, 241, 0.28);
    box-shadow: 0 0 10px rgba(99, 102, 241, 0.15);
}}

.top-nav-sep {{
    color: var(--border);
    font-size: 0.75rem;
}}

.top-nav-engine {{
    color: var(--cyan);
    font-weight: 600;
    font-size: 0.76rem;
}}

.top-nav-center {{
    display: flex;
    align-items: center;
}}

.top-nav-streak {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(99, 102, 241, 0.12) 50%, rgba(16, 185, 129, 0.1) 100%);
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 3px 14px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--text-primary);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 0 14px rgba(245, 158, 11, 0.12);
    cursor: default;
}}

.top-nav-streak:hover {{
    border-color: rgba(245, 158, 11, 0.6);
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.28);
    transform: translateY(-1px);
}}

.streak-flame {{
    display: inline-block;
    animation: flamePulse 2s infinite ease-in-out;
}}

@keyframes flamePulse {{
    0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 2px rgba(245, 158, 11, 0.4)); }}
    50% {{ transform: scale(1.22); filter: drop-shadow(0 0 6px rgba(245, 158, 11, 0.9)); }}
}}

.streak-xp {{
    color: #818CF8;
    font-weight: 800;
}}

.streak-mode {{
    color: #10B981;
    font-weight: 700;
}}

.top-nav-right {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    color: var(--emerald);
    font-weight: 600;
}}

.top-ambient-glow {{
    height: 1px;
    width: 100%;
    background: linear-gradient(90deg, transparent 0%, rgba(99, 102, 241, 0.6) 30%, rgba(6, 182, 212, 0.6) 70%, transparent 100%);
    margin-bottom: 20px;
    filter: blur(0.5px);
}}

/* Brand & Sidebar Styling */
section[data-testid="stSidebar"] {{
    background-color: var(--surface);
    border-right: 1px solid var(--border);
    backdrop-filter: blur(16px);
}}

.brand-container {{
    padding: 16px 18px;
    background: var(--hero-bg);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: var(--radius);
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.08);
}}

.brand-container::after {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 3px;
    background: var(--primary-gradient);
}}

.brand-header {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.brand-logo {{
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: var(--primary-gradient);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.4rem;
    font-weight: 900;
    box-shadow: 0 4px 18px var(--primary-glow);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}

.brand-logo:hover {{
    transform: scale(1.06) rotate(3deg);
}}

.brand-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.3rem;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    line-height: 1.15;
}}

.brand-badge {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--cyan);
    background: rgba(6, 182, 212, 0.12);
    padding: 2px 8px;
    border-radius: 999px;
    margin-top: 4px;
    border: 1px solid rgba(6, 182, 212, 0.28);
}}

.sidebar-heading {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    text-transform: uppercase;
    margin: 20px 0 8px 0;
}}

/* History Card */
.history-card {{
    background: var(--surface-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px 14px;
    margin-bottom: 8px;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    cursor: default;
}}
.history-card:hover {{
    border-color: var(--primary);
    transform: translateX(4px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25), 0 0 10px var(--primary-glow);
}}
.history-card .doc-title {{
    font-size: 0.84rem;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.history-card .doc-meta {{
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-top: 4px;
}}

.history-empty {{
    font-size: 0.82rem;
    color: var(--text-muted);
    padding: 14px;
    text-align: center;
    background: var(--surface-alt);
    border-radius: var(--radius-sm);
    border: 1px dashed var(--border);
}}

/* Hackathon Attribution Card */
.hackathon-badge-card {{
    background: var(--surface-alt);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: var(--radius);
    padding: 16px;
    margin-top: 24px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}}
.hackathon-badge-card .hb-title {{
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--indigo);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.hackathon-badge-card .hb-desc {{
    font-size: 0.76rem;
    color: var(--text-secondary);
    margin-top: 4px;
    line-height: 1.45;
}}

/* Hero Section */
.hero-wrapper {{
    background: var(--hero-bg);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: var(--radius-lg);
    padding: 34px 38px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 20px 45px -12px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(16px);
}}

.hero-wrapper::before {{
    content: '';
    position: absolute;
    top: -30%;
    right: -10%;
    width: 380px;
    height: 380px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.22) 0%, rgba(139, 92, 246, 0.08) 50%, transparent 70%);
    filter: blur(35px);
    pointer-events: none;
}}

.hero-wrapper::after {{
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, rgba(99, 102, 241, 0.5) 30%, rgba(6, 182, 212, 0.5) 70%, transparent 100%);
}}

.hero-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 4px 14px;
    border-radius: 999px;
    background: rgba(99, 102, 241, 0.14);
    color: var(--indigo);
    border: 1px solid rgba(99, 102, 241, 0.32);
    margin-bottom: 12px;
    box-shadow: 0 0 12px rgba(99, 102, 241, 0.15);
}}

.hero-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 2.45rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    line-height: 1.15;
    margin: 0;
    background: linear-gradient(135deg, #FFFFFF 25%, #E2E8F0 55%, #818CF8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 4px 24px rgba(99, 102, 241, 0.2);
}}

.hero-subtitle {{
    font-size: 1.05rem;
    color: var(--text-secondary);
    margin-top: 10px;
    max-width: 740px;
    line-height: 1.6;
}}

.feature-pills-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 18px;
}}

.feature-pill {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 6px 16px;
    border-radius: 999px;
    background: var(--surface);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    backdrop-filter: blur(10px);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}
.feature-pill:hover {{
    border-color: var(--indigo);
    color: var(--text-primary);
    background: rgba(99, 102, 241, 0.12);
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.18);
}}

/* File Uploader styling */
div[data-testid="stFileUploaderDropzone"] {{
    background-color: var(--surface-alt) !important;
    border: 2px dashed rgba(99, 102, 241, 0.35) !important;
    border-radius: var(--radius) !important;
    padding: 26px 20px !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

div[data-testid="stFileUploaderDropzone"]:hover {{
    border-color: var(--primary) !important;
    background-color: var(--surface-card) !important;
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.22), inset 0 0 20px rgba(99, 102, 241, 0.06) !important;
    transform: translateY(-2px);
}}

/* Action Button */
.stButton > button {{
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    border-radius: 11px;
    padding: 0.58rem 1.25rem;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    border: 1px solid var(--border);
    color: var(--text-primary);
    background-color: var(--surface);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}}

.stButton > button:hover {{
    border-color: var(--indigo);
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
}}

.stButton > button:active {{
    transform: translateY(0) scale(0.98);
}}

.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 55%, #4F46E5 100%);
    color: #FFFFFF !important;
    border: none;
    font-weight: 700;
    box-shadow: 0 4px 20px var(--primary-glow), inset 0 1px 0 rgba(255, 255, 255, 0.22);
}}

.stButton > button[kind="primary"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 10px 28px var(--primary-glow), 0 0 18px rgba(139, 92, 246, 0.4);
    filter: brightness(1.1);
}}

.stButton > button[kind="secondary"]:hover {{
    background-color: var(--surface-alt);
    border-color: var(--indigo);
    transform: translateY(-2px);
}}

.stDownloadButton > button {{
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    border-radius: 11px;
    background-color: var(--surface);
    color: var(--text-primary);
    border: 1px solid var(--border);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}

.stDownloadButton > button:hover {{
    background-color: var(--surface-alt);
    border-color: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
}}

/* Form inputs & selectboxes */
div[data-baseweb="input"] {{
    border-radius: 10px !important;
    border-color: var(--border) !important;
    transition: all 0.25s ease !important;
}}
div[data-baseweb="input"]:focus-within {{
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-glow) !important;
}}
div[data-baseweb="select"] {{
    border-radius: 10px !important;
}}

/* Expanders */
div[data-testid="stExpander"] {{
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--surface) !important;
    box-shadow: var(--card-shadow) !important;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}
div[data-testid="stExpander"]:hover {{
    border-color: var(--border-hover) !important;
}}

/* Meta Stats Strip */
.stats-strip {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
}}

.stat-box {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 20px;
    box-shadow: var(--card-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.04);
    display: flex;
    align-items: center;
    gap: 14px;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}
.stat-box:hover {{
    border-color: var(--primary);
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25), 0 0 16px var(--primary-glow);
}}

.stat-icon-wrap {{
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    flex-shrink: 0;
}}

.stat-icon-indigo {{ background: rgba(99, 102, 241, 0.14); color: var(--indigo); }}
.stat-icon-cyan {{ background: rgba(6, 182, 212, 0.14); color: var(--cyan); }}
.stat-icon-emerald {{ background: rgba(52, 211, 153, 0.14); color: var(--emerald); }}
.stat-icon-amber {{ background: rgba(245, 158, 11, 0.14); color: var(--amber-text); }}

.stat-info .stat-label {{
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.stat-info .stat-val {{
    font-size: 1.08rem;
    font-weight: 800;
    color: var(--text-primary);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

/* Study Sheet Cards */
.study-card {{
    background: var(--surface-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 26px 30px;
    margin-bottom: 22px;
    box-shadow: var(--card-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.06);
    position: relative;
    overflow: hidden;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}

.study-card:hover {{
    box-shadow: 0 16px 38px rgba(0, 0, 0, 0.35), 0 0 24px -6px var(--primary-glow);
    border-color: rgba(99, 102, 241, 0.4);
    transform: translateY(-3px);
}}

.study-card-header {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 16px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
}}

.study-card-icon {{
    width: 38px;
    height: 38px;
    border-radius: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
    flex-shrink: 0;
    background: var(--primary-gradient);
    color: white;
    box-shadow: 0 4px 14px var(--primary-glow);
}}

.study-card-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-primary);
}}

.study-card-body {{
    font-size: 0.96rem;
    color: var(--text-secondary);
    line-height: 1.72;
}}

.study-card-body p {{ margin-bottom: 12px; }}
.study-card-body ul {{ margin: 0; padding-left: 20px; }}
.study-card-body li {{ margin-bottom: 8px; }}
.study-card-body strong {{ color: var(--text-primary); font-weight: 700; }}
.study-card-body code {{
    background: var(--surface-alt);
    color: var(--cyan);
    padding: 3px 8px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88em;
    border: 1px solid var(--border);
}}

/* Exam Takeaways Card (Radiant Amber) */
.exam-card {{
    background: var(--amber-bg);
    border: 1px solid var(--amber-border);
    border-radius: var(--radius);
    padding: 26px 30px;
    margin-bottom: 22px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 32px rgba(245, 158, 11, 0.08), inset 0 1px 0 rgba(245, 158, 11, 0.15);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}

.exam-card:hover {{
    box-shadow: 0 16px 40px rgba(245, 158, 11, 0.16), 0 0 24px rgba(245, 158, 11, 0.25);
    border-color: rgba(245, 158, 11, 0.5);
    transform: translateY(-3px);
}}

.exam-card .study-card-icon {{
    background: linear-gradient(135deg, #F59E0B, #EA580C);
    box-shadow: 0 4px 14px rgba(245, 158, 11, 0.38);
}}

.exam-card .study-card-title {{ color: var(--amber-text); }}
.exam-card .study-card-body {{ color: var(--amber-text); }}
.exam-card .study-card-body strong {{ color: var(--amber-text); font-weight: 800; }}

/* Flashcard Styles */
.flashcard-box {{
    background: var(--surface);
    border: 2px solid var(--primary);
    border-radius: var(--radius-lg);
    padding: 42px 34px;
    min-height: 230px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    box-shadow: 0 16px 45px var(--primary-glow), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    position: relative;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}}

.flashcard-box:hover {{
    transform: translateY(-4px) scale(1.008);
    box-shadow: 0 22px 55px var(--primary-glow), 0 0 25px rgba(139, 92, 246, 0.35);
}}

.flashcard-pill {{
    position: absolute;
    top: 16px;
    left: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 3px 12px;
    border-radius: 999px;
    background: rgba(99, 102, 241, 0.14);
    color: var(--indigo);
    border: 1px solid rgba(99, 102, 241, 0.25);
}}

.flashcard-status {{
    position: absolute;
    top: 16px;
    right: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--emerald);
}}

.flashcard-term {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.7rem;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 8px;
    letter-spacing: -0.01em;
}}

.flashcard-defn {{
    font-size: 1.08rem;
    color: var(--text-secondary);
    line-height: 1.65;
    max-width: 620px;
}}

.flashcard-flip-prompt {{
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-top: 16px;
}}

/* AI Chat Message Bubbles */
.chat-bubble-user {{
    background: var(--primary-gradient);
    color: #FFFFFF;
    border-radius: 16px 16px 4px 16px;
    padding: 13px 20px;
    margin-bottom: 14px;
    max-width: 82%;
    margin-left: auto;
    font-size: 0.95rem;
    box-shadow: 0 6px 20px var(--primary-glow);
    line-height: 1.55;
}}

.chat-bubble-ai {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px 16px 16px 4px;
    padding: 16px 22px;
    margin-bottom: 16px;
    max-width: 86%;
    font-size: 0.95rem;
    color: var(--text-secondary);
    line-height: 1.7;
    box-shadow: var(--card-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.04);
}}
.chat-bubble-ai strong {{
    color: var(--text-primary);
}}

/* Quiz Section */
.quiz-card {{
    background: var(--surface-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 22px 26px;
    margin-bottom: 18px;
    box-shadow: var(--card-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.04);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}

.quiz-card:hover {{
    border-color: var(--primary);
    box-shadow: var(--card-hover-shadow), 0 0 18px -4px var(--primary-glow);
    transform: translateY(-2px);
}}

.quiz-question-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--cyan);
    background: rgba(6, 182, 212, 0.12);
    padding: 3px 12px;
    border-radius: 999px;
    margin-bottom: 10px;
    border: 1px solid rgba(6, 182, 212, 0.28);
}}

.quiz-question-text {{
    font-size: 1.08rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.52;
    margin-bottom: 12px;
}}

.quiz-answer-box {{
    background: var(--surface-alt);
    border-left: 3px solid var(--emerald);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 14px 18px;
    margin-top: 10px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}}

.quiz-ans-title {{
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--emerald);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

.quiz-ans-text {{
    font-size: 0.98rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-top: 3px;
}}

.quiz-explanation {{
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-top: 8px;
    line-height: 1.55;
}}

/* Custom Tabs Styling */
div[data-baseweb="tab-list"] {{
    gap: 6px;
    background: var(--surface);
    padding: 6px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    margin-bottom: 22px;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
}}

div[data-baseweb="tab"] {{
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 9px 18px !important;
    color: var(--text-secondary) !important;
    border: none !important;
    transition: all 0.2s ease !important;
}}

div[data-baseweb="tab"]:hover {{
    color: var(--text-primary) !important;
    background: rgba(255, 255, 255, 0.05) !important;
}}

div[data-baseweb="tab"][aria-selected="true"] {{
    background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 18px var(--primary-glow), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
}}

/* Empty State */
.empty-placeholder {{
    text-align: center;
    padding: 75px 30px;
    background: var(--surface);
    border: 1px dashed var(--border);
    border-radius: var(--radius-lg);
    color: var(--text-muted);
    box-shadow: var(--card-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.05);
    position: relative;
    overflow: hidden;
}}

.empty-placeholder::before {{
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 320px;
    height: 320px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, transparent 70%);
    pointer-events: none;
}}

.empty-icon {{
    font-size: 3.5rem;
    margin-bottom: 16px;
    display: inline-block;
    animation: floatIcon 3s ease-in-out infinite;
}}

@keyframes floatIcon {{
    0%, 100% {{ transform: translateY(0px); }}
    50% {{ transform: translateY(-8px); }}
}}

.empty-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 8px;
    letter-spacing: -0.01em;
}}

.empty-sub {{
    font-size: 0.98rem;
    color: var(--text-secondary);
    max-width: 500px;
    margin: 0 auto;
    line-height: 1.6;
}}

/* Google Auth & User Profile Design System */
.google-brand-btn {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: #FFFFFF;
    color: #1F2937 !important;
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.92rem;
    padding: 8px 18px;
    border-radius: 10px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    transition: all 0.2s ease;
    cursor: pointer;
}}
.google-brand-btn:hover {{
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
    background: #F8FAFC;
}}
.user-profile-chip {{
    display: inline-flex;
    align-items: center;
    gap: 9px;
    background: var(--surface-card);
    border: 1px solid var(--border);
    padding: 4px 14px;
    border-radius: 999px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}}
.user-chip-avatar {{
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: 2px solid var(--indigo);
}}
.user-chip-name {{
    font-weight: 700;
    font-size: 0.86rem;
    color: var(--text-primary);
}}
.user-chip-verified {{
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 999px;
    background: rgba(16, 185, 129, 0.15);
    color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.3);
}}

.user-sidebar-card {{
    background: var(--surface-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px;
    margin-bottom: 16px;
    box-shadow: var(--card-shadow);
}}
.auth-callout-card {{
    background: rgba(99, 102, 241, 0.08);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: var(--radius);
    padding: 14px;
    margin-bottom: 12px;
}}

.nav-switcher-box {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 4px 8px;
    border-radius: 12px;
    box-shadow: var(--card-shadow);
}}

/* Community Hub Styling */
.community-hero-banner {{
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.1) 50%, rgba(6, 182, 212, 0.08) 100%);
    border: 1px solid rgba(99, 102, 241, 0.28);
    border-radius: var(--radius-lg);
    padding: 28px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 35px rgba(0, 0, 0, 0.18);
}}
.community-hero-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.85rem;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 8px;
    letter-spacing: -0.02em;
}}
.community-hero-sub {{
    font-size: 0.98rem;
    color: var(--text-secondary);
    max-width: 760px;
    line-height: 1.6;
    margin-bottom: 14px;
}}

.community-card-box {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 22px;
    margin-bottom: 18px;
    transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: var(--card-shadow);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 250px;
}}
.community-card-box:hover {{
    border-color: var(--indigo);
    transform: translateY(-3px);
    box-shadow: 0 14px 34px var(--primary-glow);
}}
.community-card-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
}}
.community-card-icon-title {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.community-card-icon {{
    font-size: 1.6rem;
}}
.community-card-name {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.12rem;
    font-weight: 700;
    color: var(--text-primary);
}}
.community-card-cat {{
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 999px;
    background: rgba(99, 102, 241, 0.12);
    color: var(--indigo);
    border: 1px solid rgba(99, 102, 241, 0.25);
}}
.community-card-desc {{
    font-size: 0.88rem;
    color: var(--text-secondary);
    line-height: 1.55;
    margin-bottom: 12px;
    min-height: 42px;
}}
.community-card-topic {{
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 0.82rem;
    color: var(--text-secondary);
    margin-bottom: 12px;
}}
.community-card-footer {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 10px;
    border-top: 1px solid var(--border);
}}

.room-header-box {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: var(--card-shadow);
}}

.pomodoro-group-banner {{
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(245, 158, 11, 0.08) 100%);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: var(--radius);
    padding: 16px 22px;
    margin-bottom: 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 18px rgba(239, 68, 68, 0.08);
}}

.chat-stream-box {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
    max-height: 520px;
    overflow-y: auto;
    padding-right: 6px;
}}
.chat-entry {{
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 18px;
    transition: all 0.2s ease;
}}
.chat-entry.question-entry {{
    border-left: 4px solid #F59E0B;
    background: rgba(245, 158, 11, 0.05);
}}
.chat-entry-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
}}
.chat-avatar {{
    width: 28px;
    height: 28px;
    border-radius: 50%;
}}
.chat-sender-name {{
    font-weight: 700;
    font-size: 0.88rem;
    color: var(--text-primary);
}}
.chat-role-badge {{
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 999px;
    background: rgba(99, 102, 241, 0.15);
    color: var(--indigo);
}}
.chat-time {{
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-left: auto;
}}
.chat-text {{
    font-size: 0.92rem;
    color: var(--text-secondary);
    line-height: 1.6;
}}

.vault-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 22px;
    margin-bottom: 14px;
    box-shadow: var(--card-shadow);
    transition: all 0.2s ease;
}}
.vault-card:hover {{
    border-color: var(--border-hover);
    transform: translateY(-2px);
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Helpers & Utilities
# --------------------------------------------------------------------------
def clean_html(raw_html: str) -> str:
    """Strips leading indentation from each line so Markdown parser does not treat HTML as indented code blocks."""
    if not raw_html:
        return ""
    return re.sub(r"^[ \t]+", "", raw_html.strip(), flags=re.MULTILINE)


def get_api_key() -> str:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            key = st.secrets["GEMINI_API_KEY"]
            if key and str(key).strip():
                return str(key).strip()
    except Exception:
        pass
    return (os.getenv("GEMINI_API_KEY", "") or "").strip()


def reset_state():
    st.session_state["result"] = None
    st.session_state["quiz_feedback"] = {}
    st.session_state["flashcard_idx"] = 0
    st.session_state["flashcard_flipped"] = False
    st.session_state["flashcards_mastered"] = set()
    st.session_state["chat_history"] = []
    st.session_state["concept_search_query"] = ""
    try:
        cached_generate_revision_notes.clear()
    except Exception:
        pass


@st.cache_data(show_spinner=False, ttl=3600, max_entries=50)
def cached_generate_revision_notes(file_hash: str, text: str, subject: str, depth: str, api_key: str) -> dict:
    """
    Caches parsed revision notes by PDF content hash.
    Enables sub-second instant loads on repeated uploads or tab switches in deployment.
    """
    return generate_revision_notes(
        api_key=api_key,
        extracted_text=text,
        subject=subject,
        depth="Exhaustive" if "Exhaustive" in depth else "High-Yield",
    )


def extract_flashcards_from_result(result: dict) -> list:
    cards = []
    seen_terms = set()
    # Scan all sections for bulleted or numbered bold terms
    for heading, text in result.get("sections", {}).items():
        if "Executive Summary" in heading:
            continue
        pattern = re.compile(r"(?:[-*•]|\d+[.)])\s+\*\*([^*]+)\*\*[:\-—]?\s*(.+)", re.MULTILINE)
        for match in pattern.finditer(text):
            term = match.group(1).strip()
            defn = match.group(2).strip()
            if len(defn) > 5 and term.lower() not in seen_terms and not term.lower().startswith("note"):
                seen_terms.add(term.lower())
                cards.append({"term": term, "definition": defn})

    # If cards are still few (< 6), try looser pattern: any **Bold Term**: Definition
    if len(cards) < 6:
        for heading, text in result.get("sections", {}).items():
            if "Executive Summary" in heading:
                continue
            loose_pattern = re.compile(r"\*\*([^*:\n]+)\*\*[:\-—]\s*([^\n\r]+)")
            for match in loose_pattern.finditer(text):
                term = match.group(1).strip()
                defn = match.group(2).strip()
                if len(defn) > 5 and len(term) < 60 and term.lower() not in seen_terms and not term.lower().startswith("note"):
                    seen_terms.add(term.lower())
                    cards.append({"term": term, "definition": defn})

    # Also add quiz items if flashcards are few
    if len(cards) < 6 and result.get("quiz"):
        for q in result["quiz"]:
            if q["question"].lower() not in seen_terms:
                seen_terms.add(q["question"].lower())
                cards.append({"term": q["question"], "definition": f"{q['answer']} — {q.get('explanation', '')}"})
    return cards


SECTION_ICONS = {
    "Executive Summary": "💡",
    "Core Concepts & Definitions": "🧬",
    "Step-by-Step Mechanisms, Algorithms & Workflows": "⚙️",
    "Step-by-Step Mechanisms & Workflows": "⚙️",
    "Mechanisms, Algorithms & Workflows": "⚙️",
    "Important Formulas, Syntax, or Rules": "📐",
    "High-Yield Exam Traps & Key Takeaways": "🏆",
    "High-Yield Exam Takeaways": "🏆",
    "Comprehensive Notes": "📚",
}

SUBJECT_ICONS = {
    "General": "📚",
    "Operating Systems": "💻",
    "Discrete Mathematics": "📐",
    "Java / C++": "☕",
    "Data Structures & Algorithms": "🌲",
    "Law": "⚖️",
    "Mathematics": "∑",
    "Physics": "⚛️",
    "Business / Economics": "📊",
}


def extract_video_topics(result: dict) -> list:
    topics = []
    subject = result.get("meta", {}).get("subject", "")

    # 1. Look for subheadings in the mechanisms & workflows section
    mech_text = result.get("sections", {}).get("Step-by-Step Mechanisms, Algorithms & Workflows", "")
    subheadings = re.findall(r"###\s+([^#\n\r]+)", mech_text)
    for sh in subheadings:
        clean = sh.strip()
        if len(clean) > 3 and clean not in topics:
            topics.append(clean)

    # 2. Extract key bold terms from Core Concepts
    core_text = result.get("sections", {}).get("Core Concepts & Definitions", "")
    terms = re.findall(r"[-*•]\s+\*\*([^*]+)\*\*", core_text)
    for t in terms:
        clean = t.strip()
        if len(clean) > 3 and clean not in topics and not clean.lower().startswith("note"):
            topics.append(clean)

    # 3. Fallback topics if none extracted
    if not topics:
        base_name = result.get("meta", {}).get("base_name", "Lecture Topic")
        topics = [
            base_name.replace("_", " "),
            f"{subject} Key Concepts" if subject != "General" else "Core Concepts Overview",
            f"{subject} Exam Problem Solving" if subject != "General" else "Exam Problem Solving",
        ]

    return topics[:10]


# --------------------------------------------------------------------------
# Authentication & Community Dialogs
# --------------------------------------------------------------------------
@st.dialog("🔑 Sign in with Google / Gmail")
def show_login_dialog():
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 18px;">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">🌐</div>
            <h3 style="margin: 0; color: #6366F1; font-family: 'Outfit', sans-serif; font-size: 1.4rem;">Sign in with Google</h3>
            <p style="font-size: 0.88rem; color: #94A3B8; margin-top: 6px; line-height: 1.55;">
                Connect your authentic Google identity to unlock Collaborative Study Communities, group notes sharing, live discussions, and synchronized Pomodoro study rooms.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    email = st.text_input("Gmail Address", placeholder="e.g. yourname@gmail.com", key="dialog_login_email")
    name = st.text_input("Full Name (optional)", placeholder="e.g. Akash Kumar Gautam", key="dialog_login_name")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Sign In with Google", type="primary", use_container_width=True, key="dialog_login_submit"):
            if not email or not email.strip():
                st.error("Please enter your Gmail address.")
            elif not is_valid_gmail(email):
                st.error("Invalid email. Please provide a valid Gmail (@gmail.com, @googlemail.com, or university Google address).")
            else:
                login_user(st.session_state, email, name)
                st.toast(f"Welcome to NoteCraft, {st.session_state['user']['name']}! 🎉", icon="👋")
                st.rerun()
    with col2:
        if st.button("⚡ Quick Demo Sign In", type="secondary", use_container_width=True, key="dialog_demo_submit"):
            login_user(st.session_state, "akash.gautam@gmail.com", "Akash Kumar Gautam")
            st.toast("Signed in as Akash Kumar Gautam (Demo) 🎉", icon="👋")
            st.rerun()


@st.dialog("➕ Create New Study Community")
def show_create_community_dialog():
    user = get_current_user(st.session_state)
    st.markdown(
        """
        <p style="font-size: 0.9rem; color: #94A3B8; margin-bottom: 12px;">
            Create a collaborative study space for your university cohort, exam squad, or subject interest group.
        </p>
        """,
        unsafe_allow_html=True,
    )
    name = st.text_input("Community Name", placeholder="e.g. Distributed Systems & Cloud", key="new_comm_name")
    col_icon, col_cat = st.columns([1, 2])
    with col_icon:
        icon = st.selectbox("Icon", ["💻", "⚡", "📐", "🌐", "🧠", "🎯", "🔬", "🚀", "📚", "🤖"], index=0, key="new_comm_icon")
    with col_cat:
        category = st.selectbox("Category", ["Computer Science", "Algorithms", "Mathematics", "Software Engineering", "AI & Data Science", "Exam Prep"], index=0, key="new_comm_cat")

    desc = st.text_area("Group Description & Focus Topics", placeholder="What will members study and discuss here?", key="new_comm_desc")
    tags_str = st.text_input("Tags (comma separated)", placeholder="e.g. Cloud, Raft, Paxos", key="new_comm_tags")

    if st.button("🚀 Launch Community", type="primary", use_container_width=True, key="new_comm_submit"):
        if not name or not name.strip():
            st.error("Please enter a community name.")
        else:
            tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else ["Study", "Exam"]
            new_c = create_community(
                st.session_state,
                name=name,
                description=desc,
                category=category,
                icon=icon,
                creator_user=user,
                tags=tags,
            )
            st.session_state["active_community_id"] = new_c["id"]
            st.toast(f"🎉 Created community '{name}'!", icon="🚀")
            st.rerun()


@st.dialog("📤 Share Revision Notes to Community")
def show_share_to_community_dialog():
    user = get_current_user(st.session_state)
    result = st.session_state.get("result")
    if not result:
        st.warning("No generated revision notes found in Personal Studio.")
        return

    communities = get_all_communities(st.session_state)
    comm_names = [f"{c['icon']} {c['name']}" for c in communities]
    selected_idx = st.selectbox(
        "Select Target Community",
        range(len(communities)),
        format_func=lambda i: comm_names[i],
        key="share_comm_select",
    )
    target_comm = communities[selected_idx]

    default_title = f"{result.get('meta', {}).get('base_name', 'Lecture')} Master Revision Deck"
    deck_title = st.text_input("Deck Title", value=default_title, key="share_deck_title")
    tags_input = st.text_input(
        "Tags (comma separated)",
        value=f"{target_comm['tags'][0] if target_comm.get('tags') else 'Revision'}, CheatSheet",
        key="share_deck_tags",
    )

    if st.button("🚀 Publish to Group Vault", type="primary", use_container_width=True, key="share_deck_btn"):
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]
        share_notes_deck(
            st.session_state,
            comm_id=target_comm["id"],
            user=user,
            title=deck_title,
            content=result["raw"],
            tags=tags,
        )
        st.toast(f"🎉 Deck published to {target_comm['name']}!", icon="🚀")
        st.session_state["active_community_id"] = target_comm["id"]
        st.session_state["current_view"] = "community"
        st.rerun()


# --------------------------------------------------------------------------
# Community Co-Study Hub Main Renderer
# --------------------------------------------------------------------------
def render_community_hub_view(active_api_key: str):
    user = get_current_user(st.session_state)

    # 1. Community Hero Header
    st.markdown(
        """
        <header class="community-hero-banner" role="banner">
            <div class="hero-pill" style="display: inline-block; margin-bottom: 8px;">👥 NoteCraft Community Co-Study Hub</div>
            <h1 class="community-hero-title">Collaborative Study Communities</h1>
            <p class="community-hero-sub">
                Connect with peers across computer science, algorithms, mathematics, and exam prep.
                Ask high-yield questions, exchange master revision vaults, and tackle synchronized Pomodoro focus sprints together.
            </p>
            <div class="feature-pills-row" role="list">
                <span class="feature-pill">🌐 Live Study Rooms</span>
                <span class="feature-pill">💬 Real-Time Q&A Feed</span>
                <span class="feature-pill">📚 Shared Revision Vaults</span>
                <span class="feature-pill">⏱️ Synchronized Pomodoro</span>
                <span class="feature-pill">🔒 Google Verified Identity</span>
            </div>
        </header>
        """,
        unsafe_allow_html=True,
    )

    # 2. If user is NOT authenticated, display Google Sign-In gate
    if not user:
        st.markdown(
            """
            <div style="background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 32px; box-shadow: var(--card-shadow); margin-bottom: 30px; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 10px;">🔐</div>
                <h2 style="font-family: 'Outfit', sans-serif; font-size: 1.5rem; color: var(--text-primary); margin-bottom: 8px;">
                    Google Account Required to Access Communities
                </h2>
                <p style="color: var(--text-secondary); font-size: 0.95rem; max-width: 620px; margin: 0 auto 20px auto; line-height: 1.6;">
                    NoteCraft requires an authentic Gmail or academic Google account to join live study groups, ask exam questions, and share revision decks with fellow students.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container():
            col_login1, col_login2 = st.columns([1.5, 1])
            with col_login1:
                st.markdown("### 🔑 Sign In with your Gmail")
                l_email = st.text_input("Gmail Address", placeholder="e.g. student@gmail.com or scholar@stanford.edu", key="hub_email_in")
                l_name = st.text_input("Full Name", placeholder="e.g. Akash Kumar Gautam", key="hub_name_in")

                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    if st.button("🚀 Sign In & Enter Community", type="primary", use_container_width=True, key="hub_signin_btn"):
                        if not l_email or not l_email.strip():
                            st.error("Please provide your Gmail address.")
                        elif not is_valid_gmail(l_email):
                            st.error("Invalid email address. Please use a valid Gmail or university Google domain (@gmail.com, @googlemail.com, .edu, .ac.*).")
                        else:
                            login_user(st.session_state, l_email, l_name)
                            st.toast(f"Welcome, {st.session_state['user']['name']}! 🎉", icon="👋")
                            st.rerun()
                with b_col2:
                    if st.button("⚡ One-Click Demo Sign In", type="secondary", use_container_width=True, key="hub_demo_btn"):
                        login_user(st.session_state, "akash.gautam@gmail.com", "Akash Kumar Gautam")
                        st.toast("Signed in as Akash Kumar Gautam (Demo) 🎉", icon="👋")
                        st.rerun()

            with col_login2:
                st.markdown(
                    """
                    <div style="background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; height: 100%;">
                        <div style="font-weight: 700; color: var(--indigo); margin-bottom: 8px;">✨ What You Get as a Member:</div>
                        <ul style="color: var(--text-secondary); font-size: 0.88rem; line-height: 1.8; margin: 0; padding-left: 20px;">
                            <li>Join subject-specific co-study rooms</li>
                            <li>Ask exam questions with live answer tags</li>
                            <li>1-Click export notes from personal studio to group vault</li>
                            <li>Import classmate revision decks directly into AI tutor</li>
                            <li>Synchronized group Pomodoro focus sessions</li>
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown("### 👀 Preview Active Study Rooms")
        communities = get_all_communities(st.session_state)
        cols = st.columns(2)
        for i, comm in enumerate(communities[:4]):
            with cols[i % 2]:
                preview_card_html = (
                    f'<div class="community-card-box">'
                    f'<div>'
                    f'<div class="community-card-header">'
                    f'<div class="community-card-icon-title">'
                    f'<span class="community-card-icon">{comm["icon"]}</span>'
                    f'<span class="community-card-name">{html.escape(comm["name"])}</span>'
                    f'</div>'
                    f'<span class="community-card-cat">{html.escape(comm["category"])}</span>'
                    f'</div>'
                    f'<div class="community-card-desc">{html.escape(comm["description"])}</div>'
                    f'<div class="community-card-topic">🔥 <b>Current Focus:</b> {html.escape(comm["active_topic"])}</div>'
                    f'</div>'
                    f'<div class="community-card-footer">'
                    f'<span style="font-size: 0.82rem; color: var(--text-muted);">👥 {len(comm["members"])} students studying</span>'
                    f'<span style="font-size: 0.82rem; color: var(--indigo); font-weight: 600;">🔒 Sign in to join</span>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(preview_card_html, unsafe_allow_html=True)
        return

    # 3. Authenticated User View
    active_comm_id = st.session_state.get("active_community_id")

    # If NO community is active -> render Community Directory
    if not active_comm_id:
        top_c1, top_c2 = st.columns([3, 1.2], vertical_alignment="center")
        with top_c1:
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 12px;">
                    <img src="{user['avatar']}" style="width: 44px; height: 44px; border-radius: 50%; border: 2px solid #6366F1;" />
                    <div>
                        <div style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary);">
                            Welcome back, {html.escape(user['name'])}! 👋
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: var(--text-secondary);">
                            <span>📧 {html.escape(user['email'])}</span>
                            <span>•</span>
                            <span style="color: #10B981; font-weight: 600;">✅ Google Authorized</span>
                            <span>•</span>
                            <span>⚡ <b>{user.get('study_xp', 120)} XP</b></span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with top_c2:
            if st.button("➕ Create Study Group", type="primary", use_container_width=True, key="dir_create_group_btn"):
                show_create_community_dialog()

        # Search & Filter Controls
        all_comms = get_all_communities(st.session_state)
        categories = ["All Categories"] + sorted(list({c["category"] for c in all_comms}))

        f_col1, f_col2 = st.columns([2.5, 1.2])
        with f_col1:
            search_query = st.text_input(
                "Search communities",
                placeholder="🔍 Search by subject, topic (e.g. OS, Paging, DP, Logic)...",
                label_visibility="collapsed",
                key="comm_search_input",
            )
        with f_col2:
            selected_cat = st.selectbox(
                "Filter by Category",
                options=categories,
                index=0,
                label_visibility="collapsed",
                key="comm_cat_filter",
            )

        # Filter communities
        filtered = []
        for c in all_comms:
            match_cat = (selected_cat == "All Categories") or (c["category"] == selected_cat)
            match_query = True
            if search_query and search_query.strip():
                q = search_query.strip().lower()
                match_query = (
                    q in c["name"].lower()
                    or q in c["description"].lower()
                    or q in c["active_topic"].lower()
                    or any(q in t.lower() for t in c.get("tags", []))
                )
            if match_cat and match_query:
                filtered.append(c)

        st.markdown(f"#### 🌐 Active Study Rooms ({len(filtered)})")
        if not filtered:
            st.info("No study groups matched your search criteria. Try a different query or create a new group!")
        else:
            cols = st.columns(2)
            for idx, comm in enumerate(filtered):
                is_member = is_user_member(comm, user["email"])
                with cols[idx % 2]:
                    tags_pills = "".join([f'<span class="feature-pill" style="font-size: 0.72rem; padding: 2px 8px;">#{html.escape(t)}</span>' for t in comm.get('tags', [])])
                    comm_box_html = (
                        f'<div class="community-card-box">'
                        f'<div>'
                        f'<div class="community-card-header">'
                        f'<div class="community-card-icon-title">'
                        f'<span class="community-card-icon">{comm["icon"]}</span>'
                        f'<span class="community-card-name">{html.escape(comm["name"])}</span>'
                        f'</div>'
                        f'<span class="community-card-cat">{html.escape(comm["category"])}</span>'
                        f'</div>'
                        f'<div class="community-card-desc">{html.escape(comm["description"])}</div>'
                        f'<div class="community-card-topic">🔥 <b>Current Focus:</b> {html.escape(comm["active_topic"])}</div>'
                        f'<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;">{tags_pills}</div>'
                        f'</div>'
                        f'<div class="community-card-footer">'
                        f'<span style="font-size: 0.82rem; color: var(--text-muted);">👥 <b>{len(comm["members"])}</b> members</span>'
                        f'<span>{"⭐ Joined" if is_member else "🔓 Open"}</span>'
                        f'</div>'
                        f'</div>'
                    )
                    st.markdown(comm_box_html, unsafe_allow_html=True)
                    if is_member:
                        if st.button("🚪 Enter Study Room", key=f"btn_enter_{comm['id']}", type="primary", use_container_width=True):
                            st.session_state["active_community_id"] = comm["id"]
                            st.rerun()
                    else:
                        if st.button("➕ Join & Enter Room", key=f"btn_join_{comm['id']}", type="secondary", use_container_width=True):
                            join_community(st.session_state, comm["id"], user)
                            st.session_state["active_community_id"] = comm["id"]
                            st.toast(f"🎉 Joined {comm['name']}!", icon="👋")
                            st.rerun()

    # 4. ACTIVE COMMUNITY ROOM VIEW
    else:
        comm = get_community_by_id(st.session_state, active_comm_id)
        if not comm:
            st.session_state["active_community_id"] = None
            st.rerun()

        if not is_user_member(comm, user["email"]):
            join_community(st.session_state, comm["id"], user)

        # Header Navigation & Breadcrumbs
        h_col1, h_col2, h_col3 = st.columns([1.5, 3.5, 1.2], vertical_alignment="center")
        with h_col1:
            if st.button("← All Communities", key="room_back_btn", type="secondary", use_container_width=True):
                st.session_state["active_community_id"] = None
                st.rerun()
        with h_col2:
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 2rem;">{comm['icon']}</span>
                    <div>
                        <h2 style="margin: 0; font-family: 'Outfit', sans-serif; font-size: 1.45rem; color: var(--text-primary);">{html.escape(comm['name'])}</h2>
                        <span class="community-card-cat">{html.escape(comm['category'])}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with h_col3:
            if st.button("Leave Room", key="room_leave_btn", type="secondary", use_container_width=True):
                leave_community(st.session_state, comm["id"], user["email"])
                st.session_state["active_community_id"] = None
                st.toast("Left study room.")
                st.rerun()

        # Active Focus Topic & Live Members Avatars
        member_avatars_html = "".join([
            f'<img src="{m.get("avatar") or generate_avatar_url(m.get("name", "Student"), m.get("email", ""))}" title="{html.escape(m.get("name", "Student"))} ({m.get("role", "Member")})" style="width: 30px; height: 30px; border-radius: 50%; border: 2px solid var(--surface); margin-right: -8px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);" />'
            for m in comm.get("members", [])[:10]
        ])

        room_header_html = (
            f'<div class="room-header-box">'
            f'<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">'
            f'<div>'
            f'<div style="font-size: 0.82rem; font-weight: 700; text-transform: uppercase; color: var(--indigo); letter-spacing: 0.05em; margin-bottom: 4px;">🔥 Active Sprint Focus Topic</div>'
            f'<div style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary);">{html.escape(comm["active_topic"])}</div>'
            f'</div>'
            f'<div style="display: flex; align-items: center; gap: 12px;">'
            f'<span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600;">{len(comm["members"])} in room:</span>'
            f'<div style="display: flex; align-items: center;">{member_avatars_html}</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(room_header_html, unsafe_allow_html=True)

        # Synchronized Group Pomodoro Widget
        pomo = comm.get("pomodoro", {})
        p_status = pomo.get("status", "idle")
        is_sprint = p_status == "studying"

        p_col1, p_col2 = st.columns([3, 1.5], vertical_alignment="center")
        with p_col1:
            pomo_html = (
                f'<div class="pomodoro-group-banner">'
                f'<div style="display: flex; align-items: center; gap: 14px;">'
                f'<span style="font-size: 2rem;">{"🍅" if is_sprint else "☕"}</span>'
                f'<div>'
                f'<div style="font-weight: 700; font-size: 1.05rem; color: var(--text-primary);">'
                f'{"Active Group Focus Sprint (25 Mins)" if is_sprint else "Room Focus Timer (Idle)"}'
                f'</div>'
                f'<div style="font-size: 0.84rem; color: var(--text-secondary);">'
                f'Topic: <b>{html.escape(pomo.get("session_topic", comm["active_topic"]))}</b> • 👥 {pomo.get("participants", len(comm["members"]))} students focusing together'
                f'</div>'
                f'</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(pomo_html, unsafe_allow_html=True)
        with p_col2:
            if is_sprint:
                if st.button("⏹️ Complete Sprint", key="pomo_toggle_btn", type="secondary", use_container_width=True):
                    pomo["status"] = "idle"
                    user["study_xp"] = user.get("study_xp", 120) + 25
                    st.toast("🎉 Sprint completed! +25 Study XP awarded.", icon="🏆")
                    st.rerun()
            else:
                if st.button("▶️ Start 25m Focus Sprint", key="pomo_start_btn", type="primary", use_container_width=True):
                    pomo["status"] = "studying"
                    st.toast("🍅 Group Pomodoro sprint started! Stay focused.", icon="🔥")
                    st.rerun()

        # Room Interactive Tabs
        tab_chat, tab_vault, tab_members = st.tabs([
            f"💬 Live Discussion & Q&A ({len(comm.get('chat_messages', []))})",
            f"📚 Shared Notes Vault ({len(comm.get('shared_notes', []))})",
            f"👥 Study Group Members ({len(comm.get('members', []))})",
        ])

        # TAB 1: Live Chat & Discussion Board
        with tab_chat:
            st.caption("Ask questions, discuss challenging concepts, and co-study with peers in real-time.")
            messages = comm.get("chat_messages", [])

            if not messages:
                st.markdown(
                    clean_html(
                        """
                        <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                            💬 No messages yet. Be the first to start the discussion or ask an exam question!
                        </div>
                        """
                    ),
                    unsafe_allow_html=True,
                )
            else:
                chat_items = []
                for m in messages:
                    is_q = m.get("is_question", False)
                    q_badge = '<span style="font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; background: rgba(245, 158, 11, 0.18); color: #F59E0B; margin-left: 6px;">❓ Exam Question</span>' if is_q else ""
                    s_name = html.escape(m.get("sender_name", "Student"))
                    s_avatar = m.get("sender_avatar") or generate_avatar_url(s_name, m.get("sender_email", ""))
                    s_time = html.escape(m.get("timestamp", ""))
                    s_msg = html.escape(m.get("message", ""))
                    q_cls = "question-entry" if is_q else ""

                    chat_items.append(
                        f'<div class="chat-entry {q_cls}">'
                        f'<div class="chat-entry-header">'
                        f'<img class="chat-avatar" src="{s_avatar}" alt="{s_name}" />'
                        f'<span class="chat-sender-name">{s_name}</span>'
                        f'{q_badge}'
                        f'<span class="chat-time">{s_time}</span>'
                        f'</div>'
                        f'<div class="chat-text">{s_msg}</div>'
                        f'</div>'
                    )

                full_chat_html = f'<div class="chat-stream-box">{"".join(chat_items)}</div>'
                st.markdown(full_chat_html, unsafe_allow_html=True)

            with st.form(key=f"chat_form_{comm['id']}", clear_on_submit=True):
                c_msg1, c_msg2 = st.columns([4, 1.2])
                with c_msg1:
                    new_msg_text = st.text_input(
                        "Message",
                        placeholder="Type a message, formula, or question for the group...",
                        label_visibility="collapsed",
                    )
                with c_msg2:
                    is_question_check = st.checkbox("Mark as Question ❓", value=False)

                send_btn = st.form_submit_button("Send Message 🚀", type="primary", use_container_width=True)
                if send_btn:
                    if new_msg_text and new_msg_text.strip():
                        post_chat_message(
                            st.session_state,
                            comm_id=comm["id"],
                            user=user,
                            message=new_msg_text.strip(),
                            is_question=is_question_check,
                        )
                        st.rerun()

        # TAB 2: Shared Notes Vault
        with tab_vault:
            result = st.session_state.get("result")
            if result:
                st.markdown(
                    f"""
                    <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: var(--radius); padding: 16px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-weight: 700; color: var(--text-primary); font-size: 0.95rem;">
                                📄 Current Personal Studio Notes: <b>{html.escape(result.get('meta', {}).get('file_name', 'Lecture PDF'))}</b>
                            </div>
                            <div style="font-size: 0.82rem; color: var(--text-secondary);">
                                Share your synthesized revision sheet directly into this group's vault for classmates to read and study.
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"📤 Share '{result.get('meta', {}).get('file_name', 'Lecture PDF')}' with this Group", type="primary", use_container_width=True, key=f"share_curr_{comm['id']}"):
                    share_notes_deck(
                        st.session_state,
                        comm_id=comm["id"],
                        user=user,
                        title=f"{result.get('meta', {}).get('base_name', 'Lecture')} Master Revision Sheet",
                        content=result["raw"],
                        tags=[comm["category"], "Revision", "Master Notes"],
                    )
                    st.toast(f"🎉 Notes shared to {comm['name']} Vault!", icon="🚀")
                    st.rerun()

            vault_decks = comm.get("shared_notes", [])
            if not vault_decks:
                st.markdown(
                    """
                    <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                        📚 No revision decks shared in this group yet. Upload a lecture PDF in Personal Studio and share it here!
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                for d_idx, deck in enumerate(vault_decks):
                    tags_pills = "".join([f'<span class="feature-pill" style="font-size: 0.72rem; padding: 2px 8px;">{html.escape(t)}</span>' for t in deck.get("tags", [])])
                    v_card = (
                        f'<div class="vault-card">'
                        f'<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">'
                        f'<div style="font-family: \'Outfit\', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">📑 {html.escape(deck["title"])}</div>'
                        f'<span style="font-size: 0.75rem; color: var(--text-muted);">{html.escape(deck.get("shared_at", ""))}</span>'
                        f'</div>'
                        f'<div style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 10px;">Shared by: <b style="color: var(--indigo);">{html.escape(deck.get("shared_by", "Fellow Student"))}</b></div>'
                        f'<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;">{tags_pills}</div>'
                        f'</div>'
                    )
                    st.markdown(v_card, unsafe_allow_html=True)
                    with st.expander(f"📖 Preview Deck: {deck['title']}", expanded=False):
                        st.markdown(deck["content"])
                        if st.button("📥 Import into Personal Studio (Study with AI Tutor & Flashcards)", key=f"import_deck_{deck['id']}", type="primary"):
                            st.session_state["result"] = {
                                "sections": {"Core Concepts & Notes": deck["content"]},
                                "quiz": [],
                                "raw": deck["content"],
                                "extracted_text": deck["content"],
                                "meta": {
                                    "file_name": deck["title"],
                                    "base_name": deck["title"].replace(" ", "_"),
                                    "subject": comm.get("category", "General"),
                                    "page_count": 1,
                                    "word_count": len(deck["content"].split()),
                                    "read_time": max(1, round(len(deck["content"].split()) / 200)),
                                    "generated_at": datetime.now().strftime("%b %d, %H:%M"),
                                },
                            }
                            st.session_state["current_view"] = "studio"
                            st.toast(f"Imported '{deck['title']}' into Personal Studio!", icon="🎉")
                            st.rerun()

        # TAB 3: Study Group Members Directory
        with tab_members:
            st.caption(f"Currently registered members in {comm['name']}.")
            m_cols = st.columns(3)
            for m_i, mem in enumerate(comm.get("members", [])):
                role = mem.get("role", "Member")
                is_mod = role == "Moderator"
                mem_avatar = mem.get("avatar") or generate_avatar_url(mem.get("name", "Student"), mem.get("email", ""))
                mem_name = html.escape(mem.get("name", "Student"))
                border_color = '#F59E0B' if is_mod else '#6366F1'
                role_badge = '⭐ Moderator' if is_mod else '🧑‍🎓 Member'
                role_color = '#F59E0B' if is_mod else '#94A3B8'

                with m_cols[m_i % 3]:
                    m_card = (
                        f'<div style="background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 12px;">'
                        f'<img src="{mem_avatar}" style="width: 38px; height: 38px; border-radius: 50%; border: 2px solid {border_color};" />'
                        f'<div style="overflow: hidden;">'
                        f'<div style="font-weight: 700; font-size: 0.9rem; color: var(--text-primary); text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">{mem_name}</div>'
                        f'<div style="font-size: 0.72rem; color: {role_color}; font-weight: 600;">{role_badge}</div>'
                        f'</div>'
                        f'</div>'
                    )
                    st.markdown(m_card, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Sidebar UI
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand-container">
            <div class="brand-header">
                <div class="brand-logo">⚡</div>
                <div>
                    <div class="brand-title">NoteCraft</div>
                    <div class="brand-badge">STUDENT WORKSPACE</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Student Profile / Google Auth Sidebar Card
    user = get_current_user(st.session_state)
    if user:
        st.markdown(
            f"""
            <div class="user-sidebar-card">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <img src="{user['avatar']}" style="width: 38px; height: 38px; border-radius: 50%; border: 2px solid #6366F1;" />
                    <div style="overflow: hidden;">
                        <div style="font-weight: 700; color: var(--text-primary); font-size: 0.92rem; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">{html.escape(user['name'])}</div>
                        <div style="font-size: 0.72rem; color: #10B981; font-weight: 600;">✅ Google Authorized</div>
                    </div>
                </div>
                <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📧 {html.escape(user['email'])}</div>
                <div style="display: flex; justify-content: space-between; font-size: 0.76rem; background: var(--surface-alt); padding: 5px 10px; border-radius: 8px; border: 1px solid var(--border);">
                    <span>⚡ XP: <b style="color: #6366F1;">{user.get('study_xp', 120)}</b></span>
                    <span>🏅 Scholar</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", use_container_width=True, key="sidebar_signout_btn"):
            logout_user(st.session_state)
            st.toast("Signed out successfully.")
            st.rerun()
    else:
        st.markdown(
            """
            <div class="auth-callout-card">
                <div style="font-weight: 700; font-size: 0.86rem; color: var(--text-primary); margin-bottom: 4px;">Google Student Account</div>
                <div style="font-size: 0.76rem; color: var(--text-secondary); margin-bottom: 8px;">Sign in with Gmail to join Collaborative Study Communities.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔑 Sign In with Google", use_container_width=True, type="primary", key="sidebar_signin_btn"):
            show_login_dialog()

    st.markdown('<div class="sidebar-heading">Workspace Mode</div>', unsafe_allow_html=True)
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        if st.button(
            "📖 Studio",
            type="primary" if st.session_state.get("current_view") == "studio" else "secondary",
            use_container_width=True,
            key="sidebar_mode_studio",
        ):
            st.session_state["current_view"] = "studio"
            st.rerun()
    with m_col2:
        if st.button(
            "👥 Community",
            type="primary" if st.session_state.get("current_view") == "community" else "secondary",
            use_container_width=True,
            key="sidebar_mode_community",
        ):
            st.session_state["current_view"] = "community"
            st.rerun()

    st.markdown('<div class="sidebar-heading">Preferences</div>', unsafe_allow_html=True)
    dark_toggle = st.toggle("🌙 Dark Mode", value=st.session_state["dark_mode"])
    if dark_toggle != st.session_state["dark_mode"]:
        st.session_state["dark_mode"] = dark_toggle
        st.rerun()

    st.markdown('<div class="sidebar-heading">Subject Focus</div>', unsafe_allow_html=True)
    subject_options = list(SUBJECT_HINTS.keys())
    formatted_options = [f"{SUBJECT_ICONS.get(s, '📚')} {s}" for s in subject_options]

    selected_formatted = st.selectbox(
        "Subject",
        options=formatted_options,
        index=0,
        label_visibility="collapsed",
        help="Tailors terminology and academic focus in the generated notes.",
    )
    subject = subject_options[formatted_options.index(selected_formatted)]

    # Quick Study Timer Widget
    with st.expander("⏱️ Focus Study Timer", expanded=False):
        timer_mins = st.selectbox("Focus Duration", [5, 15, 25, 45], index=2)
        st.caption(f"Set a timer for **{timer_mins} minutes** of distraction-free active recall.")
        st.components.v1.html(
            f"""
            <div style="text-align: center; font-family: sans-serif; color: #94A3B8;">
                <div id="timerDisplay" style="font-size: 1.8rem; font-weight: 700; color: #6366F1; margin: 6px 0;">{timer_mins:02d}:00</div>
                <div style="display: flex; justify-content: center; gap: 8px;">
                    <button id="startTimer" style="background:#6366F1; color:white; border:none; padding:4px 12px; border-radius:6px; font-weight:600; cursor:pointer;">Start</button>
                    <button id="resetTimer" style="background:#334155; color:white; border:none; padding:4px 12px; border-radius:6px; font-weight:600; cursor:pointer;">Reset</button>
                </div>
            </div>
            <script>
            let totalSec = {timer_mins} * 60;
            let timerId = null;
            function update() {{
                let m = Math.floor(totalSec / 60);
                let s = totalSec % 60;
                document.getElementById('timerDisplay').innerText = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
                if (totalSec <= 0) {{
                    clearInterval(timerId);
                    document.getElementById('timerDisplay').innerText = "Done! 🎉";
                }} else {{
                    totalSec--;
                }}
            }}
            document.getElementById('startTimer').onclick = function() {{
                if (!timerId) timerId = setInterval(update, 1000);
            }};
            document.getElementById('resetTimer').onclick = function() {{
                clearInterval(timerId);
                timerId = null;
                totalSec = {timer_mins} * 60;
                document.getElementById('timerDisplay').innerText = "{timer_mins:02d}:00";
            }};
            </script>
            """,
            height=90,
        )

    with st.expander("🔑 API Key Configuration", expanded=False):
        api_key_input = st.text_input(
            "Gemini API key override",
            type="password",
            placeholder="AIzaSy...",
            help="Leave blank to use GEMINI_API_KEY from .env / Streamlit secrets.",
        )
        if get_api_key():
            st.caption("✅ Default API key detected in environment.")
        else:
            st.caption("⚠️ No default key found. Please input one above or configure in Streamlit secrets / .env.")

    st.markdown('<div class="sidebar-heading">Recent Documents</div>', unsafe_allow_html=True)
    if st.session_state["history"]:
        history_html = ""
        for item in reversed(st.session_state["history"][-5:]):
            history_html += (
                f'<div class="history-card">'
                f'  <div class="doc-title">{html.escape(item["name"])}</div>'
                f'  <div class="doc-meta"><span>{html.escape(item["subject"])}</span><span>{item["time"]}</span></div>'
                f'</div>'
            )
        st.markdown(history_html, unsafe_allow_html=True)
        if st.button("Clear History", use_container_width=True, type="secondary"):
            st.session_state["history"] = []
            st.rerun()
    else:
        st.markdown(
            '<div class="history-empty">No documents processed yet.<br>Upload a lecture PDF to start.</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="hackathon-badge-card">
            <div class="hb-title">⚡ Powered by NoteCraft</div>
            <div class="hb-desc">Built by Akash Kumar Gautam</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Main Content: Global Top Navigation Bar & Hero Header
# --------------------------------------------------------------------------
user_nav = get_current_user(st.session_state)
current_xp = user_nav.get("study_xp", 120) if user_nav else 120

st.markdown(
    f"""
    <nav class="top-nav-bar" role="navigation" aria-label="System Status and Engine Overview">
        <div class="top-nav-left">
            <span class="live-dot-pulse" aria-hidden="true"></span>
            <span class="top-nav-brand">NoteCraft Studio</span>
            <span class="top-nav-version">PRO '26</span>
            <span class="top-nav-sep" aria-hidden="true">•</span>
            <span class="top-nav-engine">⚡ Gemini 3.6 Flash Active</span>
        </div>
        <div class="top-nav-center">
            <div class="top-nav-streak" title="Daily Active Recall Streak & Brain XP Meter">
                <span class="streak-flame">🔥</span>
                <span><b>5-Day Streak</b></span>
                <span style="color: var(--border);">•</span>
                <span class="streak-xp">⚡ {current_xp} XP</span>
                <span style="color: var(--border);">•</span>
                <span class="streak-mode">🧠 Active Recall Mode</span>
            </div>
        </div>
        <div class="top-nav-right">
            <span class="top-nav-status">🟢 Engine Ready</span>
            <span class="top-nav-sep" aria-hidden="true">•</span>
            <span style="color: var(--text-muted); font-weight: 500;">Academic Session</span>
        </div>
    </nav>
    <div class="top-ambient-glow" aria-hidden="true"></div>
    """,
    unsafe_allow_html=True,
)

# Interactive Workspace Switcher & User Status Strip
top_s1, top_s2, top_s3 = st.columns([2.2, 2.8, 2.2], vertical_alignment="center")

with top_s1:
    is_comm = st.session_state.get("current_view") == "community"
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 0.84rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Workspace:</span>
            <span class="feature-pill" style="color: var(--indigo); font-weight: 700; padding: 4px 12px;">
                {'👥 Community Co-Study Hub' if is_comm else '📖 Personal Revision Studio'}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with top_s2:
    w_btn1, w_btn2 = st.columns(2)
    with w_btn1:
        if st.button("📖 Personal Studio", type="primary" if not is_comm else "secondary", use_container_width=True, key="top_switch_studio"):
            st.session_state["current_view"] = "studio"
            st.rerun()
    with w_btn2:
        if st.button("👥 Community Hub", type="primary" if is_comm else "secondary", use_container_width=True, key="top_switch_community"):
            st.session_state["current_view"] = "community"
            st.rerun()

with top_s3:
    user = get_current_user(st.session_state)
    if user:
        u_p1, u_p2 = st.columns([2.5, 1], vertical_alignment="center")
        with u_p1:
            st.markdown(
                f"""
                <div class="user-profile-chip" title="{html.escape(user['email'])}">
                    <img class="user-chip-avatar" src="{user['avatar']}" />
                    <span class="user-chip-name">{html.escape(user['name'].split()[0])}</span>
                    <span class="user-chip-verified">✓</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with u_p2:
            if st.button("Log out", key="top_logout_btn", type="secondary"):
                logout_user(st.session_state)
                st.toast("Logged out.")
                st.rerun()
    else:
        if st.button("🔑 Sign In with Google", type="primary", use_container_width=True, key="top_login_btn"):
            show_login_dialog()

# Route to Community Co-Study Hub if selected
if st.session_state.get("current_view") == "community":
    active_key = api_key_input.strip() if 'api_key_input' in locals() and api_key_input else get_api_key()
    render_community_hub_view(active_key)
    st.stop()

st.markdown(
    """
    <header class="hero-wrapper" role="banner" aria-label="NoteCraft Academic Workspace Introduction">
        <div class="hero-pill">⚡ NoteCraft AI Studio</div>
        <h1 class="hero-title">NoteCraft</h1>
        <p class="hero-subtitle">
            Transform heavy lecture PDFs into high-yield study sheets, interactive active-recall flashcards,
            self-scoring quizzes, and 24/7 AI tutor guidance.
        </p>
        <div class="feature-pills-row" role="list" aria-label="Core Studio Features">
            <span class="feature-pill" role="listitem">⚡ Powered by Gemini Flash Engine</span>
            <span class="feature-pill" role="listitem">🃏 Flip Flashcards Deck</span>
            <span class="feature-pill" role="listitem">🎯 Active Recall Quiz</span>
            <span class="feature-pill" role="listitem">🎬 Video Explainers & Shorts</span>
            <span class="feature-pill" role="listitem">💬 Ask NoteCraft AI Tutor</span>
            <span class="feature-pill" role="listitem">🎧 Audio Revision Mode</span>
        </div>
    </header>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Upload Studio Card
# --------------------------------------------------------------------------
u_col1, u_col2 = st.columns([2.5, 1.2])

with u_col1:
    uploaded_file = st.file_uploader(
        "Upload lecture material",
        type=["pdf"],
        accept_multiple_files=False,
        help="Upload lecture notes, lecture slides, syllabus, or academic papers (PDF format, max 25MB).",
    )

with u_col2:
    depth_choice = st.selectbox(
        "Coverage Depth",
        options=["🚀 Exhaustive Master Notes", "⚡ High-Yield Exam Cram"],
        index=0,
        help="Exhaustive Master Notes ensures complete, in-depth coverage across all slides, concepts, and algorithms.",
    )
    generate_clicked = st.button("✨ Craft Revision Workspace", type="primary", use_container_width=True)
    if st.session_state["result"] is not None:
        if st.button("🔄 Reset Workspace", type="secondary", use_container_width=True):
            reset_state()
            st.rerun()

# --------------------------------------------------------------------------
# Processing Pipeline
# --------------------------------------------------------------------------
if generate_clicked:
    if uploaded_file is None:
        st.toast("Please upload a PDF first!", icon="⚠️")
        st.warning("⚠️ Please select a lecture PDF file before clicking Craft Revision Workspace.")
    else:
        file_bytes = uploaded_file.read()
        size_mb = len(file_bytes) / (1024 * 1024)

        if size_mb > 25:
            st.toast("File exceeds 25 MB limit.", icon="⚠️")
            st.error(f"This file is {size_mb:.1f} MB. Please upload a PDF under 25 MB.")
        else:
            status = st.status("🚀 NoteCraft is analyzing your lecture material...", expanded=True)
            extraction = None
            try:
                status.write("📄 Reading PDF text layers and structuring pages...")
                extraction = extract_text_from_pdf(file_bytes)
            except ValueError as e:
                status.update(label="PDF extraction failed", state="error")
                st.toast("Could not read PDF.", icon="⚠️")
                st.error(str(e))

            if extraction is not None:
                if extraction.is_empty:
                    status.update(label="No extractable text found", state="error")
                    st.toast("Scanned PDF detected without text layer.", icon="⚠️")
                    st.error(
                        "No readable text could be extracted from this PDF. It appears to be "
                        "a scanned document without OCR text. Please use an OCR'd or digital PDF."
                    )
                else:
                    if extraction.warning:
                        status.write(f"⚠️ Notice: {extraction.warning}")

                    status.write(f"✅ Extracted {extraction.page_count} pages. Synthesizing concepts...")
                    time.sleep(0.3)

                    active_api_key = api_key_input.strip() or get_api_key()

                    file_hash = hashlib.md5(file_bytes).hexdigest()
                    status.write("🧠 Prompting Gemini Flash Engine for study sheets & quiz...")
                    try:
                        parsed = cached_generate_revision_notes(
                            file_hash=file_hash,
                            text=extraction.text,
                            subject=subject,
                            depth=depth_choice,
                            api_key=active_api_key,
                        )
                        # Validate that cached result is complete and healthy
                        if not parsed or not parsed.get("sections") or (len(parsed.get("quiz", [])) == 0 and len(parsed.get("sections", {})) <= 1):
                            cached_generate_revision_notes.clear()
                            parsed = generate_revision_notes(
                                api_key=active_api_key,
                                extracted_text=extraction.text,
                                subject=subject,
                                depth="Exhaustive" if "Exhaustive" in depth_choice else "High-Yield",
                            )

                        status.update(label="✨ NoteCraft study materials generated successfully!", state="complete", expanded=False)

                        # Estimate read time (~200 words per minute)
                        total_words = len(parsed["raw"].split())
                        est_read_time = max(1, round(total_words / 200))

                        st.session_state["result"] = {
                            "sections": parsed["sections"],
                            "quiz": parsed["quiz"],
                            "raw": parsed["raw"],
                            "extracted_text": extraction.text,
                            "meta": {
                                "file_name": uploaded_file.name,
                                "base_name": os.path.splitext(uploaded_file.name)[0],
                                "subject": subject,
                                "page_count": extraction.page_count,
                                "word_count": total_words,
                                "read_time": est_read_time,
                                "generated_at": datetime.now().strftime("%b %d, %H:%M"),
                            },
                        }
                        st.session_state["history"].append({
                            "name": uploaded_file.name,
                            "subject": subject,
                            "time": datetime.now().strftime("%H:%M"),
                        })
                        st.session_state["quiz_feedback"] = {}
                        st.session_state["flashcard_idx"] = 0
                        st.session_state["flashcard_flipped"] = False
                        st.session_state["flashcards_mastered"] = set()
                        st.session_state["chat_history"] = []
                        st.toast("NoteCraft workspace is ready!", icon="🎉")
                        st.rerun()
                    except GeminiAPIError as e:
                        status.update(label="Generation failed", state="error")
                        st.toast("Gemini API error occurred.", icon="⚠️")
                        st.error(f"{e}")
                        if "503" in str(e) or "unavailable" in str(e).lower() or "high demand" in str(e).lower():
                            st.info("💡 **Traffic Spike Notice:** Google's Gemini servers are experiencing temporary high demand spikes. NoteCraft has automatic fallback protection. Please wait 5 seconds and click **Craft Revision Workspace** again.")


# --------------------------------------------------------------------------
# Results Workspace
# --------------------------------------------------------------------------
result = st.session_state["result"]

if result is not None:
    meta = result["meta"]
    flashcards = extract_flashcards_from_result(result)

    # --- Stats Strip ---
    st.markdown(
        f"""
        <div class="stats-strip">
            <div class="stat-box">
                <div class="stat-icon-wrap stat-icon-indigo">📄</div>
                <div class="stat-info">
                    <div class="stat-label">Document</div>
                    <div class="stat-val" title="{html.escape(meta['file_name'])}">{html.escape(meta['file_name'])}</div>
                </div>
            </div>
            <div class="stat-box">
                <div class="stat-icon-wrap stat-icon-cyan">⏱️</div>
                <div class="stat-info">
                    <div class="stat-label">Est. Study Time</div>
                    <div class="stat-val">~{meta['read_time']} min read</div>
                </div>
            </div>
            <div class="stat-box">
                <div class="stat-icon-wrap stat-icon-emerald">🃏</div>
                <div class="stat-info">
                    <div class="stat-label">Active Flashcards</div>
                    <div class="stat-val">{len(flashcards)} Flashcards</div>
                </div>
            </div>
            <div class="stat-box">
                <div class="stat-icon-wrap stat-icon-amber">🎯</div>
                <div class="stat-info">
                    <div class="stat-label">Practice Quiz</div>
                    <div class="stat-val">{len(result['quiz'])} Exam Questions</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Action Bar (Export, Copy & Community Share) ---
    act_col1, act_col2, act_col3, act_col4 = st.columns([1.5, 1.5, 2.2, 2.0])
    with act_col1:
        st.download_button(
            label="📥 Download Markdown",
            data=result["raw"].encode("utf-8"),
            file_name=f"{meta['base_name']}_notecraft.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with act_col2:
        clean_text_js = result["raw"].replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        st.components.v1.html(
            f"""
            <button id="copyBtn" style="
                width: 100%;
                height: 38px;
                background: #1E293B;
                color: #F8FAFC;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px;
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 0.88rem;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                transition: all 0.2s ease;
            ">
                📋 Copy All Notes
            </button>
            <script>
            document.getElementById("copyBtn").addEventListener("click", function() {{
                const content = `{clean_text_js}`;
                navigator.clipboard.writeText(content).then(() => {{
                    this.innerHTML = "✅ Copied to Clipboard!";
                    this.style.background = "#10B981";
                    setTimeout(() => {{
                        this.innerHTML = "📋 Copy All Notes";
                        this.style.background = "#1E293B";
                    }}, 2000);
                }});
            }});
            </script>
            """,
            height=46,
        )
    with act_col3:
        if st.button("👥 Share to Community Vault", use_container_width=True, key="action_bar_share_comm_btn", type="primary"):
            if not is_authenticated(st.session_state):
                show_login_dialog()
            else:
                show_share_to_community_dialog()

    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

    # --- Workspace Tabs ---
    tab_notes, tab_flashcards, tab_quiz, tab_tutor, tab_videos, tab_audio, tab_raw = st.tabs([
        "📚 Study Sheet",
        f"🃏 Flashcards ({len(flashcards)})",
        f"🧠 Practice Quiz ({len(result['quiz'])})",
        "💬 Ask NoteCraft AI",
        "🎬 Video Explainers",
        "🎧 Audio Revision",
        "📄 Raw Notes & Export",
    ])

    # --------------------------------------------------------------------------
    # Tab 1: Structured Study Sheet (with Concept Search)
    # --------------------------------------------------------------------------
    with tab_notes:
        search_col, _ = st.columns([2, 1])
        with search_col:
            search_query = st.text_input(
                "Search notes",
                placeholder="🔍 Filter concepts, definitions, or keywords in this study sheet...",
                label_visibility="collapsed",
            ).strip().lower()

        for heading, content in result["sections"].items():
            # If user searches, filter paragraphs/lines in the content
            if search_query:
                lines = content.split("\n")
                filtered_lines = [l for l in lines if search_query in l.lower() or l.startswith("#")]
                if not filtered_lines or (len(filtered_lines) == 1 and filtered_lines[0].startswith("#")):
                    continue
                display_content = "\n".join(filtered_lines)
            else:
                display_content = content

            is_takeaways = "Exam Takeaways" in heading
            icon = SECTION_ICONS.get(heading, "📌")
            card_class = "exam-card" if is_takeaways else "study-card"

            card_html = (
                f'<article class="{card_class}" role="article" aria-label="{html.escape(heading)}">'
                f'  <div class="study-card-header">'
                f'    <div class="study-card-icon" aria-hidden="true">{icon}</div>'
                f'    <div class="study-card-title">{html.escape(heading)}</div>'
                f'  </div>'
                f'  <div class="study-card-body">\n\n{display_content}\n\n</div>'
                f'</article>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # Tab 2: Interactive Flashcards Deck (Flip & Active Recall)
    # --------------------------------------------------------------------------
    with tab_flashcards:
        if not flashcards:
            st.info("No concept terms detected to generate flashcards.")
        else:
            cur_idx = st.session_state["flashcard_idx"]
            if cur_idx >= len(flashcards):
                cur_idx = 0
                st.session_state["flashcard_idx"] = 0

            card = flashcards[cur_idx]
            is_flipped = st.session_state["flashcard_flipped"]
            is_mastered = cur_idx in st.session_state["flashcards_mastered"]

            # Flashcard Header info
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="font-weight: 700; color: var(--text-primary);">Card {cur_idx + 1} of {len(flashcards)}</span>
                    <span style="font-weight: 700; color: var(--emerald);">⭐ Mastered: {len(st.session_state['flashcards_mastered'])} / {len(flashcards)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Card Container
            status_text = "🌟 Mastered" if is_mastered else ""
            if not is_flipped:
                card_html = f"""
                <div class="flashcard-box">
                    <div class="flashcard-pill">CONCEPT TERM</div>
                    <div class="flashcard-status">{status_text}</div>
                    <div class="flashcard-term">{html.escape(card['term'])}</div>
                    <div class="flashcard-flip-prompt">💡 Click "Flip Card" below to reveal the definition</div>
                </div>
                """
            else:
                card_html = f"""
                <div class="flashcard-box" style="border-color: var(--cyan); background: var(--surface-alt);">
                    <div class="flashcard-pill" style="color: var(--cyan); background: rgba(6, 182, 212, 0.12);">DEFINITION & DETAILS</div>
                    <div class="flashcard-status">{status_text}</div>
                    <div class="flashcard-term" style="font-size: 1.25rem; color: var(--cyan); margin-bottom: 12px;">{html.escape(card['term'])}</div>
                    <div class="flashcard-defn">{html.escape(card['definition'])}</div>
                </div>
                """
            st.markdown(card_html, unsafe_allow_html=True)
            st.markdown("<div style='height: 14px'></div>", unsafe_allow_html=True)

            # Controls: Previous, Flip, Next, Mark Mastered
            fc_col1, fc_col2, fc_col3, fc_col4 = st.columns([1, 1.5, 1, 1.5])

            with fc_col1:
                if st.button("⬅️ Previous", use_container_width=True, disabled=(cur_idx == 0)):
                    st.session_state["flashcard_idx"] = max(0, cur_idx - 1)
                    st.session_state["flashcard_flipped"] = False
                    st.rerun()

            with fc_col2:
                flip_label = "🔄 Flip to Front" if is_flipped else "🔄 Flip to Reveal"
                if st.button(flip_label, type="primary", use_container_width=True):
                    st.session_state["flashcard_flipped"] = not is_flipped
                    st.rerun()

            with fc_col3:
                if st.button("Next ➡️", use_container_width=True, disabled=(cur_idx == len(flashcards) - 1)):
                    st.session_state["flashcard_idx"] = min(len(flashcards) - 1, cur_idx + 1)
                    st.session_state["flashcard_flipped"] = False
                    st.rerun()

            with fc_col4:
                master_btn_label = "✅ Unmark Mastered" if is_mastered else "⭐ Mark Mastered"
                if st.button(master_btn_label, use_container_width=True):
                    if is_mastered:
                        st.session_state["flashcards_mastered"].remove(cur_idx)
                    else:
                        st.session_state["flashcards_mastered"].add(cur_idx)
                    st.rerun()

    # --------------------------------------------------------------------------
    # Tab 3: Interactive Quiz Mode (Self-Testing & Scoring)
    # --------------------------------------------------------------------------
    with tab_quiz:
        st.markdown(
            """
            <div style="margin-bottom: 16px;">
                <p style="color: var(--text-secondary); font-size: 0.95rem; margin: 0;">
                    Self-test your exam readiness! Read each question, test your recall, then reveal the solution.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        quiz = result["quiz"]
        if not quiz:
            st.info("No quiz questions were generated for this material.")
        else:
            for idx, q in enumerate(quiz):
                with st.container():
                    st.markdown(
                        f"""
                        <div class="quiz-card">
                            <div class="quiz-question-badge">Question {idx + 1} of {len(quiz)}</div>
                            <div class="quiz-question-text">{html.escape(q['question'])}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    with st.expander(f"👁️ Reveal Answer & Explanation for Question {idx + 1}"):
                        expl_html = f'<div class="quiz-explanation">{html.escape(q["explanation"])}</div>' if q.get("explanation") else ""
                        st.markdown(
                            f"""
                            <div class="quiz-answer-box">
                                <div class="quiz-ans-title">Correct Answer</div>
                                <div class="quiz-ans-text">{html.escape(q['answer'])}</div>
                                {expl_html}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # Interactive Self-Assessment feedback buttons
                        fb_col1, fb_col2, fb_spacer = st.columns([1.5, 1.5, 4])
                        with fb_col1:
                            if st.button("🎯 Got it right!", key=f"right_{idx}", type="secondary"):
                                st.session_state["quiz_feedback"][idx] = "mastered"
                                st.rerun()
                        with fb_col2:
                            if st.button("🔄 Review later", key=f"review_{idx}", type="secondary"):
                                st.session_state["quiz_feedback"][idx] = "review"
                                st.rerun()

                        status_val = st.session_state["quiz_feedback"].get(idx)
                        if status_val == "mastered":
                            st.caption("🌟 Marked as **Mastered**! Great job!")
                        elif status_val == "review":
                            st.caption("🔖 Marked for **Review**. Practice makes perfect!")

                    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

            mastered_count = sum(1 for v in st.session_state["quiz_feedback"].values() if v == "mastered")
            st.markdown(
                f"""
                <div style="background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 18px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
                    <span style="font-weight: 600; color: var(--text-primary);">Quiz Mastery Score:</span>
                    <span style="font-weight: 800; color: var(--indigo); font-size: 1.1rem;">{mastered_count} / {len(quiz)} Mastered</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------------------------
    # Tab 4: "Ask NoteCraft" AI Tutor Chat
    # --------------------------------------------------------------------------
    with tab_tutor:
        st.markdown(
            """
            <div style="margin-bottom: 16px;">
                <p style="color: var(--text-secondary); font-size: 0.95rem;">
                    Have questions about the uploaded lecture? Ask NoteCraft for analogies, real-world examples, or step-by-step breakdowns.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Quick starter prompt chips
        q_chips_col1, q_chips_col2, q_chips_col3 = st.columns(3)
        with q_chips_col1:
            if st.button("💡 Explain this simply with an analogy", use_container_width=True):
                st.session_state["user_chat_input"] = "Can you explain the main concept in this lecture with a simple real-world analogy?"
        with q_chips_col2:
            if st.button("⚠️ Common student mistakes & traps", use_container_width=True):
                st.session_state["user_chat_input"] = "What are common pitfalls or mistakes students make on this topic during exams?"
        with q_chips_col3:
            if st.button("📝 2 more practice questions", use_container_width=True):
                st.session_state["user_chat_input"] = "Can you give me 2 additional practice questions with solutions on this topic?"

        # Display conversation history
        for msg in st.session_state["chat_history"]:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-bubble-user">{html.escape(msg["content"])}</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="chat-bubble-ai"><strong style="color: var(--indigo);">NoteCraft AI Tutor:</strong><br>{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

        # Chat input box
        default_val = st.session_state.pop("user_chat_input", "")
        with st.form("tutor_chat_form", clear_on_submit=True):
            user_question = st.text_input("Ask a question about this lecture:", value=default_val, placeholder="e.g. Can you explain formula #2 in step-by-step detail?")
            send_btn = st.form_submit_button("🚀 Ask NoteCraft", type="primary")

        if send_btn and user_question.strip():
            st.session_state["chat_history"].append({"role": "user", "content": user_question.strip()})
            active_api_key = api_key_input.strip() or get_api_key()
            with st.spinner("NoteCraft AI is thinking..."):
                try:
                    ai_answer = ask_gemini_question(
                        api_key=active_api_key,
                        context_text=result.get("extracted_text", result["raw"]),
                        question=user_question.strip(),
                    )
                    st.session_state["chat_history"].append({"role": "assistant", "content": ai_answer})
                    st.rerun()
                except GeminiAPIError as err:
                    st.error(f"Error querying NoteCraft AI: {err}")

    # --------------------------------------------------------------------------
    # Tab 5: Video Explanations & YouTube Shorts
    # --------------------------------------------------------------------------
    with tab_videos:
        st.markdown(
            """
            <div style="margin-bottom: 16px;">
                <p style="color: var(--text-secondary); font-size: 0.95rem;">
                    Launch verified educational video tutorials, 60-second animated Shorts, and university walkthroughs for any concept in your lecture.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        video_topics = extract_video_topics(result)
        selected_topic = st.selectbox(
            "Select a topic to explore video tutorials:",
            options=video_topics,
            index=0,
            help="Choose any concept from your notes to open verified video explanations and Shorts.",
        )

        subject_name = result["meta"]["subject"]
        clean_subj = subject_name if subject_name != "General" else ""
        encoded_topic = urllib.parse.quote_plus(f"{selected_topic} {clean_subj}".strip())
        yt_search_url = f"https://www.youtube.com/results?search_query={encoded_topic}+lecture"
        yt_shorts_url = f"https://www.youtube.com/results?search_query={encoded_topic}+shorts"
        yt_animation_url = f"https://www.youtube.com/results?search_query={encoded_topic}+animation+visualization"

        v_col1, v_col2 = st.columns([1.6, 1.2])

        with v_col1:
            st.markdown(
                f"""
                <div style="background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 26px 28px; box-shadow: var(--card-shadow); position: relative; overflow: hidden;">
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                        <div style="width: 44px; height: 44px; border-radius: 12px; background: linear-gradient(135deg, #FF0000, #CC0000); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; color: white; box-shadow: 0 4px 14px rgba(255,0,0,0.3);">
                            🎬
                        </div>
                        <div>
                            <div style="font-size: 0.72rem; font-weight: 700; color: #EF4444; letter-spacing: 0.05em; text-transform: uppercase;">
                                Verified Educational Video Hub
                            </div>
                            <div style="font-family: 'Outfit', sans-serif; font-size: 1.25rem; font-weight: 800; color: var(--text-primary);">
                                {html.escape(selected_topic)}
                            </div>
                        </div>
                    </div>
                    <p style="font-size: 0.92rem; color: var(--text-secondary); line-height: 1.6; margin-bottom: 22px;">
                        Watch verified topic-specific visual animations, step-by-step lecture walkthroughs, and rapid 60-second concept Shorts on YouTube with zero restrictions.
                    </p>
                    <div style="display: flex; flex-wrap: wrap; gap: 12px;" role="navigation" aria-label="Video Tutorial Links">
                        <a href="{yt_shorts_url}" target="_blank" rel="noopener noreferrer" role="link" aria-label="Watch 60-Second YouTube Shorts on {html.escape(selected_topic)}" style="
                            display: inline-flex; align-items: center; gap: 8px;
                            background: linear-gradient(135deg, #FF0000, #B91C1C);
                            color: #FFFFFF !important; font-weight: 700; font-size: 0.92rem;
                            padding: 10px 20px; border-radius: 10px; text-decoration: none;
                            box-shadow: 0 4px 16px rgba(239, 68, 68, 0.35);
                            transition: all 0.2s ease;
                        ">
                            <span aria-hidden="true">📱</span> Watch 60-Second YouTube Shorts
                        </a>
                        <a href="{yt_search_url}" target="_blank" rel="noopener noreferrer" role="link" aria-label="Open Full University Lectures on {html.escape(selected_topic)}" style="
                            display: inline-flex; align-items: center; gap: 8px;
                            background: var(--surface-alt);
                            color: var(--text-primary) !important; font-weight: 600; font-size: 0.92rem;
                            padding: 10px 18px; border-radius: 10px; text-decoration: none;
                            border: 1px solid var(--border);
                            transition: all 0.2s ease;
                        ">
                            <span aria-hidden="true">📺</span> Open Full University Lectures
                        </a>
                        <a href="{yt_animation_url}" target="_blank" rel="noopener noreferrer" role="link" aria-label="Visual Concept Animations for {html.escape(selected_topic)}" style="
                            display: inline-flex; align-items: center; gap: 8px;
                            background: var(--surface-alt);
                            color: var(--cyan) !important; font-weight: 600; font-size: 0.92rem;
                            padding: 10px 18px; border-radius: 10px; text-decoration: none;
                            border: 1px solid rgba(6, 182, 212, 0.25);
                            transition: all 0.2s ease;
                        ">
                            <span aria-hidden="true">✨</span> Visual Concept Animations
                        </a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with v_col2:
            st.markdown(
                f"""
                <div style="background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; box-shadow: var(--card-shadow); height: 100%;">
                    <div style="font-family: 'Outfit', sans-serif; font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                        <span>💡 Quick Study Strategy</span>
                    </div>
                    <ul style="font-size: 0.86rem; color: var(--text-secondary); line-height: 1.65; margin: 0; padding-left: 18px;">
                        <li style="margin-bottom: 8px;"><b>Shorts:</b> Ideal for rapid active recall and memorizing definitions.</li>
                        <li style="margin-bottom: 8px;"><b>Full Lectures:</b> Essential for tracing Gantt charts, formula proofs, and algorithm edge cases.</li>
                        <li style="margin-bottom: 8px;"><b>Animations:</b> Perfect for building visual intuition before attempting exam practice questions.</li>
                    </ul>
                    <div style="margin-top: 16px; padding: 10px 12px; background: var(--surface); border-radius: 8px; border: 1px solid var(--border); font-size: 0.78rem; color: var(--text-muted);">
                        🎯 <b>Topic:</b> {html.escape(selected_topic)} ({html.escape(subject_name)})
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------------------------
    # Tab 5: Audio Study Mode (Browser Web Speech API)
    # --------------------------------------------------------------------------
    with tab_audio:
        st.markdown(
            """
            <div style="margin-bottom: 16px;">
                <p style="color: var(--text-secondary); font-size: 0.95rem;">
                    Listen to your revision notes hands-free! Choose any section, track real-time elapsed & remaining duration, adjust playback speed, and follow live highlighted narration.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        def clean_md_for_speech(text: str) -> str:
            t = re.sub(r"```[\s\S]*?```", "", text)
            t = re.sub(r"`[^`]+`", "", t)
            t = re.sub(r"^#{1,6}\s+", "", t, flags=re.MULTILINE)
            t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
            t = re.sub(r"\*([^*]+)\*", r"\1", t)
            t = re.sub(r"^\s*[-*•]\s+", "", t, flags=re.MULTILINE)
            t = re.sub(r"\|", " ", t)
            t = re.sub(r"-{3,}", " ", t)
            t = re.sub(r"\s+", " ", t).strip()
            return t

        speech_sections = {}
        # 1. High-Yield Exam Cram (Executive Summary + Exam Traps)
        exec_summary = result["sections"].get("Executive Summary", "")
        traps = ""
        for k, v in result["sections"].items():
            if "Exam" in k or "Trap" in k or "Takeaway" in k:
                traps = v
                break
        cram_text = f"Executive Summary. {exec_summary}. High-Yield Exam Takeaways. {traps}".strip()
        speech_sections["⚡ High-Yield Exam Cram"] = clean_md_for_speech(cram_text)

        # 2. Individual sections
        for heading, content in result["sections"].items():
            speech_sections[f"📌 {heading}"] = clean_md_for_speech(f"{heading}. {content}")

        # 3. Complete Master Notes
        full_text = " ".join(f"{h}. {c}" for h, c in result["sections"].items())
        speech_sections["📚 Complete Master Notes"] = clean_md_for_speech(full_text)

        speech_sections_json = json.dumps(speech_sections).replace("</", "<\\/")

        st.components.v1.html(
            f"""
            <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: transparent;
                color: #F8FAFC;
                font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            .player-card {{
                background: #111726;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
                padding: 20px 24px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
            }}
            .header-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 14px;
                margin-bottom: 16px;
            }}
            .title-group {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .studio-icon {{
                font-size: 1.5rem;
                background: rgba(99, 102, 241, 0.15);
                border: 1px solid rgba(99, 102, 241, 0.3);
                width: 42px;
                height: 42px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 10px;
            }}
            .title-text {{
                font-size: 1.08rem;
                font-weight: 700;
                color: #F8FAFC;
            }}
            .subtitle-text {{
                font-size: 0.8rem;
                color: #94A3B8;
                margin-top: 2px;
            }}
            .section-select-wrap {{
                flex-grow: 1;
                max-width: 320px;
                min-width: 200px;
            }}
            .section-select {{
                width: 100%;
                background: #1E293B;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 0.85rem;
                font-weight: 600;
                outline: none;
                cursor: pointer;
            }}
            .section-select:focus {{
                border-color: #6366F1;
            }}

            /* Time & Progress */
            .time-box {{
                background: rgba(15, 23, 42, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 14px 18px;
                margin-bottom: 16px;
            }}
            .time-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.88rem;
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            }}
            .time-elapsed {{
                font-weight: 700;
                color: #818CF8;
                font-size: 1.05rem;
            }}
            .time-pill {{
                font-family: 'Plus Jakarta Sans', sans-serif;
                background: rgba(99, 102, 241, 0.15);
                color: #A5B4FC;
                border: 1px solid rgba(99, 102, 241, 0.3);
                padding: 3px 12px;
                border-radius: 999px;
                font-size: 0.76rem;
                font-weight: 600;
            }}
            .time-total {{
                color: #94A3B8;
                font-size: 0.95rem;
            }}
            .progress-bar-wrap {{
                width: 100%;
                height: 8px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 999px;
                margin: 10px 0 4px;
                cursor: pointer;
                position: relative;
            }}
            .progress-bar-fill {{
                height: 100%;
                width: 0%;
                background: linear-gradient(90deg, #6366F1, #06B6D4);
                border-radius: 999px;
                transition: width 0.15s linear;
            }}
            .progress-thumb {{
                position: absolute;
                top: 50%;
                left: 0%;
                transform: translate(-50%, -50%);
                width: 14px;
                height: 14px;
                background: #FFFFFF;
                border-radius: 50%;
                box-shadow: 0 0 8px rgba(99, 102, 241, 0.8);
                display: none;
                pointer-events: none;
            }}
            .progress-bar-wrap:hover .progress-thumb {{
                display: block;
            }}

            /* Controls & Speed */
            .controls-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 12px;
            }}
            .btn-group {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .btn-ctrl {{
                background: rgba(255, 255, 255, 0.08);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 0.86rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }}
            .btn-ctrl:hover {{
                background: rgba(255, 255, 255, 0.16);
            }}
            .btn-play {{
                background: linear-gradient(135deg, #6366F1, #8B5CF6);
                color: white;
                border: none;
                padding: 9px 22px;
                font-size: 0.95rem;
                font-weight: 700;
                box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
            }}
            .btn-play:hover {{
                transform: translateY(-1px);
                box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
            }}
            .speed-group {{
                display: flex;
                align-items: center;
                gap: 5px;
                flex-wrap: wrap;
            }}
            .speed-label {{
                font-size: 0.78rem;
                font-weight: 600;
                color: #94A3B8;
                margin-right: 2px;
            }}
            .speed-pill {{
                background: rgba(255, 255, 255, 0.06);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 9px;
                font-size: 0.78rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
            }}
            .speed-pill:hover {{
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.12);
            }}
            .speed-pill.active {{
                background: #6366F1;
                color: #FFFFFF;
                border-color: #6366F1;
                box-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
            }}

            /* Equalizer */
            .equalizer-wrap {{
                display: inline-flex;
                align-items: center;
                gap: 3px;
                height: 18px;
                padding: 0 4px;
            }}
            .eq-bar {{
                width: 3px;
                background: #818CF8;
                border-radius: 2px;
                height: 4px;
                transition: height 0.2s ease;
            }}
            .playing .eq-bar:nth-child(1) {{ animation: eqAnim 0.7s infinite ease-in-out; }}
            .playing .eq-bar:nth-child(2) {{ animation: eqAnim 0.5s infinite ease-in-out 0.1s; }}
            .playing .eq-bar:nth-child(3) {{ animation: eqAnim 0.9s infinite ease-in-out 0.2s; }}
            .playing .eq-bar:nth-child(4) {{ animation: eqAnim 0.6s infinite ease-in-out 0.15s; }}
            .playing .eq-bar:nth-child(5) {{ animation: eqAnim 0.8s infinite ease-in-out 0.05s; }}
            @keyframes eqAnim {{
                0%, 100% {{ height: 4px; }}
                50% {{ height: 18px; }}
            }}

            /* Teleprompter */
            .teleprompter-box {{
                margin-top: 16px;
                background: rgba(0, 0, 0, 0.35);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px 16px;
                max-height: 110px;
                overflow-y: auto;
                font-size: 0.86rem;
                line-height: 1.6;
                color: #CBD5E1;
            }}
            .teleprompter-sentence {{
                display: inline;
                padding: 2px 4px;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            .teleprompter-sentence:hover {{
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.08);
            }}
            .teleprompter-sentence.active {{
                background: rgba(99, 102, 241, 0.28);
                color: #38BDF8;
                font-weight: 600;
                box-shadow: 0 0 8px rgba(56, 189, 248, 0.25);
            }}
            #statusLine {{
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 12px;
                font-size: 0.82rem;
                color: #34D399;
            }}
            </style>

            <script id="sectionsData" type="application/json">
            {speech_sections_json}
            </script>

            <div class="player-card">
                <div class="header-row">
                    <div class="title-group">
                        <div class="studio-icon">🎧</div>
                        <div>
                            <div class="title-text">Audio Revision Studio</div>
                            <div class="subtitle-text">Browser Natural Voice • Interactive Scrubber & Speed Controls</div>
                        </div>
                    </div>
                    <div class="section-select-wrap">
                        <select id="sectionSelect" class="section-select"></select>
                    </div>
                </div>

                <!-- Time & Scrubber Box -->
                <div class="time-box">
                    <div class="time-row">
                        <span id="timeElapsed" class="time-elapsed">00:00</span>
                        <span id="timePill" class="time-pill">⏱️ ~0m 00s remaining</span>
                        <span id="timeTotal" class="time-total">00:00</span>
                    </div>
                    <div id="progressBarWrap" class="progress-bar-wrap">
                        <div id="progressBarFill" class="progress-bar-fill"></div>
                        <div id="progressThumb" class="progress-thumb"></div>
                    </div>
                </div>

                <!-- Controls Bar -->
                <div class="controls-row">
                    <div class="btn-group">
                        <button id="rewindBtn" class="btn-ctrl" title="Rewind 10 seconds">⏪ -10s</button>
                        <button id="playBtn" class="btn-ctrl btn-play">▶️ Play Audio</button>
                        <button id="forwardBtn" class="btn-ctrl" title="Forward 10 seconds">⏩ +10s</button>
                        <button id="stopBtn" class="btn-ctrl" title="Reset to start">⏹️ Reset</button>
                    </div>

                    <div class="speed-group">
                        <span class="speed-label">⚡ Speed:</span>
                        <button class="speed-pill" data-rate="0.8">0.8x</button>
                        <button class="speed-pill active" data-rate="1.0">1.0x</button>
                        <button class="speed-pill" data-rate="1.25">1.25x</button>
                        <button class="speed-pill" data-rate="1.5">1.5x</button>
                        <button class="speed-pill" data-rate="2.0">2.0x</button>
                    </div>
                </div>

                <div id="statusLine">
                    <div id="equalizer" class="equalizer-wrap">
                        <div class="eq-bar"></div>
                        <div class="eq-bar"></div>
                        <div class="eq-bar"></div>
                        <div class="eq-bar"></div>
                        <div class="eq-bar"></div>
                    </div>
                    <span id="statusText">Ready to play</span>
                </div>

                <!-- Live Highlighted Teleprompter -->
                <div id="teleprompter" class="teleprompter-box" title="Click any sentence to listen from that point"></div>
            </div>

            <script>
            let synth = window.speechSynthesis;
            let sections = JSON.parse(document.getElementById('sectionsData').textContent);
            let sectionKeys = Object.keys(sections);
            let currentSectionKey = sectionKeys[0] || '';
            let sentences = [];
            let currentIdx = 0;
            let isPlaying = false;
            let isPaused = false;
            let currentRate = 1.0;
            let currentUtterance = null;
            let timerInterval = null;
            let elapsedSec = 0;
            let totalEstSec = 0;

            // Populate Section Dropdown
            let selectEl = document.getElementById('sectionSelect');
            sectionKeys.forEach(k => {{
                let opt = document.createElement('option');
                opt.value = k;
                opt.innerText = k;
                selectEl.appendChild(opt);
            }});

            selectEl.onchange = function() {{
                loadSection(this.value);
            }};

            function formatTime(s) {{
                let m = Math.floor(s / 60);
                let sec = Math.floor(s % 60);
                return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
            }}

            function loadSection(key) {{
                stopAudio();
                currentSectionKey = key;
                let text = sections[key] || '';
                let raw = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text];
                sentences = raw.map(s => s.trim()).filter(s => s.length > 0);
                if (sentences.length === 0) sentences = [text];

                currentIdx = 0;
                elapsedSec = 0;

                let words = text.split(/\\s+/).filter(w => w.length > 0).length;
                totalEstSec = Math.max(1, Math.round((words / 2.5) / currentRate));

                updateTimerUI();
                renderTeleprompter();
                updateProgressUI(0);
            }}

            function updateTimerUI() {{
                document.getElementById('timeElapsed').innerText = formatTime(elapsedSec);
                document.getElementById('timeTotal').innerText = formatTime(totalEstSec);
                let remain = Math.max(0, totalEstSec - elapsedSec);
                let remM = Math.floor(remain / 60);
                let remS = Math.floor(remain % 60);
                document.getElementById('timePill').innerText = '⏱️ ~' + remM + 'm ' + (remS < 10 ? '0' : '') + remS + 's remaining';
            }}

            function updateProgressUI(pct) {{
                pct = Math.min(100, Math.max(0, pct));
                document.getElementById('progressBarFill').style.width = pct + '%';
                document.getElementById('progressThumb').style.left = pct + '%';
            }}

            function renderTeleprompter() {{
                let container = document.getElementById('teleprompter');
                container.innerHTML = '';
                sentences.forEach((s, idx) => {{
                    let span = document.createElement('span');
                    span.id = 'sent_' + idx;
                    span.className = 'teleprompter-sentence' + (idx === currentIdx ? ' active' : '');
                    span.innerText = s + ' ';
                    span.onclick = function() {{
                        jumpToSentence(idx);
                    }};
                    container.appendChild(span);
                }});
            }}

            function highlightSentence(idx) {{
                document.querySelectorAll('.teleprompter-sentence').forEach(el => el.classList.remove('active'));
                let activeEl = document.getElementById('sent_' + idx);
                if (activeEl) {{
                    activeEl.classList.add('active');
                    activeEl.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                }}
            }}

            function speakCurrentSentence() {{
                if (currentIdx >= sentences.length) {{
                    stopAudio();
                    return;
                }}
                highlightSentence(currentIdx);

                let pct = (currentIdx / sentences.length) * 100;
                updateProgressUI(pct);
                elapsedSec = Math.round((currentIdx / sentences.length) * totalEstSec);
                updateTimerUI();

                if (synth) synth.cancel();
                currentUtterance = new SpeechSynthesisUtterance(sentences[currentIdx]);
                currentUtterance.rate = currentRate;
                currentUtterance.pitch = 1.0;

                currentUtterance.onend = function() {{
                    if (isPlaying && !isPaused) {{
                        currentIdx++;
                        speakCurrentSentence();
                    }}
                }};

                currentUtterance.onerror = function(e) {{
                    if (isPlaying && !isPaused && e.error !== 'canceled' && e.error !== 'interrupted') {{
                        currentIdx++;
                        speakCurrentSentence();
                    }}
                }};

                if (synth) synth.speak(currentUtterance);
            }}

            function playAudio() {{
                if (!synth) {{
                    alert("Speech synthesis is not supported in this browser.");
                    return;
                }}
                if (isPaused) {{
                    isPaused = false;
                    isPlaying = true;
                    setPlayingState(true, false);
                    speakCurrentSentence();
                    startTimer();
                    return;
                }}
                isPlaying = true;
                isPaused = false;
                setPlayingState(true, false);
                speakCurrentSentence();
                startTimer();
            }}

            function pauseAudio() {{
                if (!isPlaying) return;
                isPlaying = false;
                isPaused = true;
                if (synth) synth.cancel();
                setPlayingState(false, true);
                stopTimer();
            }}

            function stopAudio() {{
                isPlaying = false;
                isPaused = false;
                if (synth) synth.cancel();
                currentIdx = 0;
                elapsedSec = 0;
                stopTimer();
                setPlayingState(false, false);
                updateProgressUI(0);
                updateTimerUI();
                highlightSentence(0);
            }}

            function jumpToSentence(idx) {{
                currentIdx = Math.max(0, Math.min(sentences.length - 1, idx));
                let wasPlaying = isPlaying;
                if (wasPlaying) {{
                    if (synth) synth.cancel();
                    speakCurrentSentence();
                }} else {{
                    highlightSentence(currentIdx);
                    let pct = (currentIdx / sentences.length) * 100;
                    updateProgressUI(pct);
                    elapsedSec = Math.round((currentIdx / sentences.length) * totalEstSec);
                    updateTimerUI();
                }}
            }}

            function setPlayingState(playing, paused) {{
                let playBtn = document.getElementById('playBtn');
                let eq = document.getElementById('equalizer');
                let st = document.getElementById('statusText');
                if (playing) {{
                    playBtn.innerHTML = '⏸️ Pause';
                    playBtn.style.background = 'linear-gradient(135deg, #EF4444, #F59E0B)';
                    eq.classList.add('playing');
                    st.innerText = '🔊 Playing revision notes...';
                }} else if (paused) {{
                    playBtn.innerHTML = '▶️ Resume';
                    playBtn.style.background = 'linear-gradient(135deg, #6366F1, #8B5CF6)';
                    eq.classList.remove('playing');
                    st.innerText = '⏸️ Paused';
                }} else {{
                    playBtn.innerHTML = '▶️ Play Audio';
                    playBtn.style.background = 'linear-gradient(135deg, #6366F1, #8B5CF6)';
                    eq.classList.remove('playing');
                    st.innerText = 'Ready to play';
                }}
            }}

            function startTimer() {{
                stopTimer();
                timerInterval = setInterval(function() {{
                    if (isPlaying && !isPaused) {{
                        elapsedSec = Math.min(totalEstSec, elapsedSec + 1);
                        updateTimerUI();
                    }}
                }}, 1000);
            }}

            function stopTimer() {{
                if (timerInterval) {{
                    clearInterval(timerInterval);
                    timerInterval = null;
                }}
            }}

            document.getElementById('playBtn').onclick = function() {{
                if (isPlaying) {{
                    pauseAudio();
                }} else {{
                    playAudio();
                }}
            }};

            document.getElementById('stopBtn').onclick = function() {{
                stopAudio();
            }};

            document.getElementById('rewindBtn').onclick = function() {{
                jumpToSentence(currentIdx - 2);
            }};

            document.getElementById('forwardBtn').onclick = function() {{
                jumpToSentence(currentIdx + 2);
            }};

            document.getElementById('progressBarWrap').onclick = function(e) {{
                let rect = this.getBoundingClientRect();
                let clickX = e.clientX - rect.left;
                let pct = clickX / rect.width;
                let targetIdx = Math.floor(sentences.length * pct);
                jumpToSentence(targetIdx);
            }};

            document.querySelectorAll('.speed-pill').forEach(btn => {{
                btn.onclick = function() {{
                    document.querySelectorAll('.speed-pill').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentRate = parseFloat(this.dataset.rate);

                    let words = (sections[currentSectionKey] || '').split(/\\s+/).filter(w => w.length > 0).length;
                    totalEstSec = Math.max(1, Math.round((words / 2.5) / currentRate));
                    updateTimerUI();

                    if (isPlaying) {{
                        if (synth) synth.cancel();
                        speakCurrentSentence();
                    }}
                }};
            }});

            // Initial load
            loadSection(currentSectionKey);
            </script>
            """,
            height=460,
        )

    # --------------------------------------------------------------------------
    # Tab 6: Raw Markdown & Export
    # --------------------------------------------------------------------------
    with tab_raw:
        st.caption("Copy this clean markdown directly into Notion, Obsidian, Roam, or Anki.")
        st.code(result["raw"], language="markdown")

else:
    st.markdown(
        """
        <section class="empty-placeholder" role="status" aria-live="polite" aria-label="Welcome placeholder">
            <div class="empty-icon" aria-hidden="true">⚡</div>
            <h2 class="empty-title">Welcome to NoteCraft</h2>
            <p class="empty-sub">
                Drop your lecture slides, notes, or syllabus PDF above and click <b>Craft Revision Workspace</b>
                to generate structured study sheets, flip flashcards, active recall quizzes, and interactive AI tutoring.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
