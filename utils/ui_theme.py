"""
UI theme for AI Resume Analyzer — dark, futuristic, scanner-inspired.

Design intent: the app's job is to "scan" a resume and report a verdict,
so the visual language leans on terminal/radar cues — mono numerals for
scores, a mint→violet gradient as the signature accent, and thin glowing
borders instead of heavy card shadows.
"""

import streamlit as st

# ---------------------------------------------------------
# Tokens
# ---------------------------------------------------------

BG = "#0B0F19"
SURFACE = "#131826"
SURFACE_2 = "#1A2133"
BORDER = "#232B40"
ACCENT = "#00E5A0"      # mint — "pass" / primary signal
ACCENT_2 = "#6C5CE7"    # violet — secondary / ML signal
TEXT = "#E6E9F0"
TEXT_MUTED = "#8B93A7"
DANGER = "#FF6B6B"
WARNING = "#FFC857"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap');

:root {{
    --bg: {BG};
    --surface: {SURFACE};
    --surface-2: {SURFACE_2};
    --border: {BORDER};
    --accent: {ACCENT};
    --accent-2: {ACCENT_2};
    --text: {TEXT};
    --text-muted: {TEXT_MUTED};
    --danger: {DANGER};
    --warning: {WARNING};
}}

.stApp {{
    background:
        radial-gradient(circle at 12% -10%, #16203A 0%, transparent 45%),
        radial-gradient(circle at 100% 0%, #1B1530 0%, transparent 40%),
        var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
}}

h1, h2, h3 {{
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.01em;
}}

h1 {{
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700 !important;
    padding-bottom: 4px;
}}

p, span, label, .stMarkdown {{
    color: var(--text);
}}

/* Tabs as pill nav */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    background: var(--surface);
    padding: 6px;
    border-radius: 14px;
    border: 1px solid var(--border);
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 10px;
    color: var(--text-muted);
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
    padding: 8px 18px;
}}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    color: #08101A !important;
}}

/* Buttons */
.stButton > button {{
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    color: #08101A;
    border: none;
    border-radius: 10px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    padding: 0.55em 1.5em;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(0, 229, 160, 0.22);
    color: #08101A;
}}
.stDownloadButton > button {{
    background: var(--surface-2);
    color: var(--accent);
    border: 1px solid var(--accent);
    border-radius: 10px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
}}
.stDownloadButton > button:hover {{
    background: var(--accent);
    color: #08101A;
}}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {{
    background: var(--surface);
    border: 1.5px dashed var(--border);
    border-radius: 12px;
}}

/* Text inputs / areas / select */
.stTextArea textarea, .stTextInput input, .stSelectbox [data-baseweb="select"] > div {{
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}}

/* Native progress bars (used for bulk-compare table context, etc.) */
div[data-testid="stProgress"] > div > div {{
    background: linear-gradient(90deg, var(--accent-2), var(--accent)) !important;
    border-radius: 6px;
}}

/* Expanders */
details {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2px 10px;
}}
summary {{
    font-family: 'Space Grotesk', sans-serif;
    color: var(--text);
}}

/* Metrics */
[data-testid="stMetric"] {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px 20px;
}}
[data-testid="stMetricValue"] {{
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--accent) !important;
}}
[data-testid="stMetricLabel"] {{
    color: var(--text-muted) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}}

/* Tables */
[data-testid="stTable"] table {{
    background: var(--surface);
    border-radius: 10px;
    overflow: hidden;
}}

/* Chat bubbles */
[data-testid="stChatMessage"] {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
}}

/* Caption / muted text */
.stCaption, [data-testid="stCaptionContainer"] {{
    color: var(--text-muted) !important;
}}

/* Success / warning / error boxes */
[data-testid="stAlert"] {{
    border-radius: 12px;
    border: 1px solid var(--border);
}}
</style>
"""


def inject_theme() -> None:
    """Call once near the top of app.py, right after st.set_page_config."""
    st.markdown(CSS, unsafe_allow_html=True)


def _score_color(score: int) -> str:
    if score >= 75:
        return ACCENT
    if score >= 50:
        return WARNING
    return DANGER


def _score_label(score: int) -> str:
    if score >= 75:
        return "Strong match"
    if score >= 50:
        return "Needs work"
    return "Low match"


def render_score_card(score: int) -> str:
    """HTML for a custom ATS score card, color-coded by band."""
    color = _score_color(score)
    label = _score_label(score)
    return f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-left:3px solid {color};
                border-radius:14px;padding:20px 26px;display:flex;align-items:center;gap:22px;margin:8px 0 18px 0;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:2.6rem;font-weight:700;color:{color};line-height:1;">
            {score}<span style="font-size:1.15rem;color:var(--text-muted);">/100</span>
        </div>
        <div>
            <div style="font-family:'Space Grotesk',sans-serif;font-weight:600;color:var(--text);font-size:1rem;">
                ATS Score
            </div>
            <div style="color:{color};font-size:0.85rem;font-weight:500;">{label}</div>
        </div>
    </div>
    """


def render_match_bar(label: str, pct: float, rank: int = 0) -> str:
    """HTML for a single labeled, gradient-filled match/confidence bar."""
    pct = max(0, min(100, pct))
    return f"""
    <div style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;font-size:0.92rem;color:var(--text);margin-bottom:5px;">
            <span style="font-family:'Inter',sans-serif;">{label}</span>
            <span style="font-family:'JetBrains Mono',monospace;color:var(--accent);">{pct}%</span>
        </div>
        <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:6px;height:10px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:linear-gradient(90deg, var(--accent-2), var(--accent));border-radius:6px;"></div>
        </div>
    </div>
    """


def render_section_header(text: str, eyebrow: str = "") -> str:
    """HTML for a styled section header with optional small eyebrow label above it."""
    eyebrow_html = (
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;'
        f'letter-spacing:0.08em;color:var(--accent-2);text-transform:uppercase;margin-bottom:2px;">{eyebrow}</div>'
        if eyebrow else ""
    )
    return f"""
    <div style="margin:18px 0 10px 0;">
        {eyebrow_html}
        <div style="font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:1.15rem;color:var(--text);">{text}</div>
    </div>
    """
