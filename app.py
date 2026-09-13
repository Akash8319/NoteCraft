"""
NoteCraft AI
------------
Single-flow app: Lecture PDF -> structured revision notes + flashcards + interactive quiz + AI tutor.

Built for: Prompt Wars Hackathon (Google for Developers x Hack2Skill x Android Club, VIT Bhopal)
Problem statement: AI-Powered Student Workspace (Flow: Lecture PDF -> revision notes)
"""

import os
import re
import time
import html
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

.top-nav-hackathon {{
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--text-secondary);
    letter-spacing: 0.03em;
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
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Helpers & Utilities
# --------------------------------------------------------------------------
def get_api_key() -> str:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "")


def reset_state():
    st.session_state["result"] = None
    st.session_state["quiz_feedback"] = {}
    st.session_state["flashcard_idx"] = 0
    st.session_state["flashcard_flipped"] = False
    st.session_state["flashcards_mastered"] = set()
    st.session_state["chat_history"] = []
    st.session_state["concept_search_query"] = ""


def extract_flashcards_from_result(result: dict) -> list:
    cards = []
    seen_terms = set()
    # Scan all sections for bulleted bold terms
    for heading, text in result.get("sections", {}).items():
        if "Executive Summary" in heading:
            continue
        pattern = re.compile(r"[-*•]\s+\*\*([^*]+)\*\*[:\-—]?\s*(.+)", re.MULTILINE)
        for match in pattern.finditer(text):
            term = match.group(1).strip()
            defn = match.group(2).strip()
            if len(defn) > 5 and term.lower() not in seen_terms and not term.lower().startswith("note"):
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
            st.caption("⚠️ No default key found. Please input one above or in .env.")

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
            <div class="hb-title">🏆 Prompt Wars Hackathon</div>
            <div class="hb-desc">Google for Developers × Hack2Skill × Android Club (VIT Bhopal)<br>Powered by NoteCraft & Gemini 3.6 Flash</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Main Content: Global Top Navigation Bar & Hero Header
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="top-nav-bar">
        <div class="top-nav-left">
            <span class="live-dot-pulse"></span>
            <span class="top-nav-brand">NoteCraft Studio</span>
            <span class="top-nav-version">PRO '26</span>
            <span class="top-nav-sep">•</span>
            <span class="top-nav-engine">⚡ Gemini 3.6 Flash Active</span>
        </div>
        <div class="top-nav-center">
            <span class="top-nav-hackathon">🏆 Google for Developers × Prompt Wars '26</span>
        </div>
        <div class="top-nav-right">
            <span class="top-nav-status">🟢 Engine Ready</span>
            <span class="top-nav-sep">•</span>
            <span style="color: var(--text-muted); font-weight: 500;">Academic Session</span>
        </div>
    </div>
    <div class="top-ambient-glow"></div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="hero-wrapper">
        <div class="hero-pill">⚡ NoteCraft AI Studio</div>
        <h1 class="hero-title">NoteCraft</h1>
        <p class="hero-subtitle">
            Transform heavy lecture PDFs into high-yield study sheets, interactive active-recall flashcards,
            self-scoring quizzes, and 24/7 AI tutor guidance.
        </p>
        <div class="feature-pills-row">
            <span class="feature-pill">⚡ Powered by Gemini 3.6 Flash</span>
            <span class="feature-pill">🃏 Flip Flashcards Deck</span>
            <span class="feature-pill">🎯 Active Recall Quiz</span>
            <span class="feature-pill">🎬 Video Explainers & Shorts</span>
            <span class="feature-pill">💬 Ask NoteCraft AI Tutor</span>
            <span class="feature-pill">🎧 Audio Revision Mode</span>
        </div>
    </div>
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

                    status.write("🧠 Prompting Gemini 3.6 Flash for exhaustive study sheets & quiz...")
                    try:
                        parsed = generate_revision_notes(
                            api_key=active_api_key,
                            extracted_text=extraction.text,
                            subject=subject,
                            depth="Exhaustive" if "Exhaustive" in depth_choice else "High-Yield",
                            status_callback=lambda msg: status.write(msg),
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

    # --- Action Bar (Export & Copy) ---
    act_col1, act_col2, act_col3 = st.columns([1.5, 1.5, 4])
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
                f'<div class="{card_class}">'
                f'  <div class="study-card-header">'
                f'    <div class="study-card-icon">{icon}</div>'
                f'    <div class="study-card-title">{html.escape(heading)}</div>'
                f'  </div>'
                f'  <div class="study-card-body">\n\n{display_content}\n\n</div>'
                f'</div>'
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
                    <div style="display: flex; flex-wrap: wrap; gap: 12px;">
                        <a href="{yt_shorts_url}" target="_blank" style="
                            display: inline-flex; align-items: center; gap: 8px;
                            background: linear-gradient(135deg, #FF0000, #B91C1C);
                            color: #FFFFFF !important; font-weight: 700; font-size: 0.92rem;
                            padding: 10px 20px; border-radius: 10px; text-decoration: none;
                            box-shadow: 0 4px 16px rgba(239, 68, 68, 0.35);
                            transition: all 0.2s ease;
                        ">
                            📱 Watch 60-Second YouTube Shorts
                        </a>
                        <a href="{yt_search_url}" target="_blank" style="
                            display: inline-flex; align-items: center; gap: 8px;
                            background: var(--surface-alt);
                            color: var(--text-primary) !important; font-weight: 600; font-size: 0.92rem;
                            padding: 10px 18px; border-radius: 10px; text-decoration: none;
                            border: 1px solid var(--border);
                            transition: all 0.2s ease;
                        ">
                            📺 Open Full University Lectures
                        </a>
                        <a href="{yt_animation_url}" target="_blank" style="
                            display: inline-flex; align-items: center; gap: 8px;
                            background: var(--surface-alt);
                            color: var(--cyan) !important; font-weight: 600; font-size: 0.92rem;
                            padding: 10px 18px; border-radius: 10px; text-decoration: none;
                            border: 1px solid rgba(6, 182, 212, 0.25);
                            transition: all 0.2s ease;
                        ">
                            ✨ Visual Concept Animations
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
        summary_text = result["sections"].get("Executive Summary", "")
        takeaways_text = result["sections"].get("High-Yield Exam Takeaways", "")
        combined_speech_text = f"Executive Summary. {summary_text}. High-Yield Exam Takeaways. {takeaways_text}"
        clean_speech = combined_speech_text.replace('"', '\\"').replace("\n", " ")

        st.markdown(
            """
            <div style="margin-bottom: 16px;">
                <p style="color: var(--text-secondary); font-size: 0.95rem;">
                    Listen to your revision notes hands-free! Powered directly by your browser's natural speech synthesizer.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.components.v1.html(
            f"""
            <div style="
                background: #131826;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 14px;
                padding: 24px;
                color: #F8FAFC;
                font-family: 'Plus Jakarta Sans', sans-serif;
            ">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;">
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 700;">🎧 Audio Revision Reader</div>
                        <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">
                            Reads the Executive Summary & Exam Takeaways aloud.
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button id="playAudioBtn" style="
                            background: linear-gradient(135deg, #6366F1, #8B5CF6);
                            color: white;
                            border: none;
                            padding: 8px 18px;
                            border-radius: 8px;
                            font-weight: 600;
                            cursor: pointer;
                            font-size: 0.9rem;
                        ">▶️ Play Audio</button>
                        <button id="stopAudioBtn" style="
                            background: rgba(255,255,255,0.08);
                            color: #F8FAFC;
                            border: 1px solid rgba(255,255,255,0.15);
                            padding: 8px 18px;
                            border-radius: 8px;
                            font-weight: 600;
                            cursor: pointer;
                            font-size: 0.9rem;
                        ">⏹️ Stop</button>
                    </div>
                </div>
                <div id="audioStatus" style="font-size: 0.82rem; color: #34D399; margin-top: 14px; display: none;">
                    🔊 NoteCraft audio reader is currently playing...
                </div>
            </div>

            <script>
            let synth = window.speechSynthesis;
            let utterance = null;
            const textToSpeak = "{clean_speech}";

            document.getElementById("playAudioBtn").addEventListener("click", function() {{
                if (!synth) {{
                    alert("Speech synthesis is not supported in this browser.");
                    return;
                }}
                synth.cancel();
                utterance = new SpeechSynthesisUtterance(textToSpeak);
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                
                document.getElementById("audioStatus").style.display = "block";
                
                utterance.onend = function() {{
                    document.getElementById("audioStatus").style.display = "none";
                }};
                
                synth.speak(utterance);
            }});

            document.getElementById("stopAudioBtn").addEventListener("click", function() {{
                if (synth) {{
                    synth.cancel();
                    document.getElementById("audioStatus").style.display = "none";
                }}
            }});
            </script>
            """,
            height=140,
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
        <div class="empty-placeholder">
            <div class="empty-icon">⚡</div>
            <div class="empty-title">Welcome to NoteCraft</div>
            <div class="empty-sub">
                Drop your lecture slides, notes, or syllabus PDF above and click <b>Craft Revision Workspace</b>
                to generate structured study sheets, flip flashcards, active recall quizzes, and interactive AI tutoring.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
