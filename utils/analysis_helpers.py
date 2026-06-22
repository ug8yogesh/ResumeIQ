"""
Helper functions for AI Resume Analyzer.
Keeps app.py focused on UI flow; all parsing/scoring logic lives here.
"""

import re
import html
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT


def compute_match_score(resume_text: str, job_description: str) -> float:
    """
    Cosine similarity between resume and JD using a fresh TF-IDF vectorizer
    fit only on these two documents (independent of the role-classifier
    vectorizer, which is trained on a fixed vocabulary).
    Returns a percentage 0-100.
    """
    try:
        tfidf = TfidfVectorizer(stop_words="english")
        vectors = tfidf.fit_transform([resume_text, job_description])
        score = cosine_similarity(vectors[0], vectors[1])[0][0]
        return round(score * 100, 1)
    except Exception:
        return 0.0


def get_top_roles(model, resume_vector, top_n: int = 3):
    """
    Returns list of (role, confidence_pct) tuples, sorted descending.
    Falls back to a single prediction with 100% confidence if the model
    doesn't support predict_proba.
    """
    if hasattr(model, "predict_proba"):
        try:
            probs = model.predict_proba(resume_vector)[0]
            classes = model.classes_
            ranked = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)
            return [(role, round(p * 100, 1)) for role, p in ranked[:top_n]]
        except Exception:
            pass
    # Fallback: no probability support
    predicted = model.predict(resume_vector)[0]
    return [(predicted, 100.0)]


def extract_section(analysis_text: str, section_name: str) -> list[str]:
    """
    Pulls bullet points under a given section heading (e.g. 'Missing Keywords')
    out of the Gemini-generated analysis text. Returns a list of clean strings.
    """
    pattern = rf"{re.escape(section_name)}:\s*(.*?)(?=\n[A-Z][A-Za-z ]+:|\Z)"
    match = re.search(pattern, analysis_text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
    block = match.group(1)
    items = re.findall(r"^[\s]*[-*•]\s*(.+)$", block, re.MULTILINE)
    return [i.strip() for i in items if i.strip()]


def extract_ats_score(analysis_text: str) -> int | None:
    """Pulls the numeric ATS score (e.g. 'ATS Score: 78/100') out of the analysis text."""
    match = re.search(r"ATS Score:\s*(\d{1,3})\s*/\s*100", analysis_text, re.IGNORECASE)
    if match:
        return min(int(match.group(1)), 100)
    return None


def highlight_keywords_html(resume_text: str, keywords: list[str]) -> str:
    """
    Returns HTML-escaped resume text with any keyword occurrences wrapped
    in <mark> tags, for use with st.markdown(..., unsafe_allow_html=True).
    """
    escaped = html.escape(resume_text)
    for kw in sorted(set(keywords), key=len, reverse=True):
        kw_clean = kw.strip()
        if not kw_clean or len(kw_clean) < 2:
            continue
        pattern = re.compile(re.escape(html.escape(kw_clean)), re.IGNORECASE)
        escaped = pattern.sub(
            lambda m: f"<mark style='background-color:#ffec99;padding:1px 3px;border-radius:3px'>{m.group(0)}</mark>",
            escaped,
        )
    return f"<div style='white-space:pre-wrap;line-height:1.6;font-size:0.9rem'>{escaped}</div>"


SECTION_HEADERS = [
    "experience", "work experience", "professional experience",
    "education", "academic background",
    "skills", "technical skills", "key skills",
    "projects", "personal projects",
    "certifications", "certificates",
    "summary", "objective", "profile",
    "achievements", "accomplishments",
]


def split_resume_sections(resume_text: str) -> dict[str, str]:
    """
    Best-effort heuristic split of resume text into common sections based on
    line-level header matching. Returns {section_name: content}. Anything
    before the first detected header goes under 'Header / Contact Info'.
    """
    lines = resume_text.splitlines()
    sections: dict[str, list[str]] = {"Header / Contact Info": []}
    current = "Header / Contact Info"

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower().strip(":").strip()
        if 2 <= len(lower.split()) <= 4 and any(
            lower == h or lower.startswith(h) for h in SECTION_HEADERS
        ):
            current = stripped.title()
            sections.setdefault(current, [])
            continue
        sections[current].append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def build_pdf_report(title: str, analysis_text: str) -> bytes:
    """
    Renders the ATS analysis text as a simple formatted PDF and returns
    the raw bytes, ready for st.download_button.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    body_style = styles["Normal"]
    body_style.alignment = TA_LEFT

    story = [Paragraph(title, styles["Title"]), Spacer(1, 16)]

    for block in analysis_text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        first = lines[0].strip()
        if first.endswith(":") or first.isupper():
            story.append(Paragraph(first, styles["Heading2"]))
            remainder = "<br/>".join(html.escape(l) for l in lines[1:])
            if remainder:
                story.append(Paragraph(remainder, body_style))
        else:
            story.append(Paragraph("<br/>".join(html.escape(l) for l in lines), body_style))
        story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
