import streamlit as st
import pickle
import google.generativeai as genai
from dotenv import load_dotenv
import os

from utils.pdf_reader import extract_text_from_pdf
from utils.analysis_helpers import (
    compute_match_score,
    get_top_roles,
    extract_section,
    extract_ats_score,
    highlight_keywords_html,
    split_resume_sections,
    build_pdf_report,
)
from utils.ui_theme import (
    inject_theme,
    render_score_card,
    render_match_bar,
    render_section_header,
)

# ---------------------------------------------------------
# Setup
# ---------------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="AI Resume Analyzer", layout="wide", page_icon="📡")
inject_theme()

st.title("AI Resume Analyzer")
st.caption("Scan your resume against any job description — ATS score, role match, and rewrite suggestions.")

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY is not set. Add it to your .env file and restart the app.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

MAX_FILE_SIZE_MB = 5
GEMINI_MODEL_NAME = "gemini-2.5-flash"


# ---------------------------------------------------------
# Cached resource loading
# ---------------------------------------------------------

@st.cache_resource
def load_models():
    try:
        with open("models/model.pkl", "rb") as f:
            model = pickle.load(f)
        with open("models/vectorizer.pkl", "rb") as f:
            vectorizer = pickle.load(f)
        return model, vectorizer
    except FileNotFoundError as e:
        st.error(f"Model file not found: {e}. Check that models/model.pkl and models/vectorizer.pkl exist.")
        st.stop()
    except Exception as e:
        st.error(f"Failed to load model files: {e}")
        st.stop()


model, vectorizer = load_models()


def call_gemini(prompt: str) -> str | None:
    """Thin wrapper around the Gemini call with consistent error handling."""
    try:
        gemini = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = gemini.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API error: {e}")
        return None


# ---------------------------------------------------------
# Session state (history, chat)
# ---------------------------------------------------------

if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: filename, role, score, analysis, resume_text, jd

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "active_resume" not in st.session_state:
    st.session_state.active_resume = None  # {"text": ..., "jd": ...} used by the chat tab


# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------

tab_single, tab_bulk, tab_cover, tab_chat, tab_history = st.tabs(
    ["🔍 Single Analysis", "📊 Bulk Compare", "✉️ Cover Letter", "💬 Chat with Resume", "🕘 History"]
)


# ===========================================================
# TAB 1 — Single Analysis
# ===========================================================
with tab_single:

    uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], key="single_upload")
    job_description = st.text_area("Paste Job Description", height=200, key="single_jd")

    if st.button("Analyze Resume", key="single_analyze_btn"):

        if uploaded_file is None:
            st.warning("Please upload a resume.")
            st.stop()

        if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            st.error(f"File too large. Please upload a PDF under {MAX_FILE_SIZE_MB} MB.")
            st.stop()

        if not job_description or not job_description.strip():
            st.warning("Please enter a Job Description.")
            st.stop()

        try:
            with st.spinner("Extracting text from resume..."):
                resume_text = extract_text_from_pdf(uploaded_file)
        except Exception as e:
            st.error(f"Failed to extract text from PDF: {e}")
            st.stop()

        if not resume_text or not resume_text.strip():
            st.error("No text could be extracted from this PDF. It may be a scanned image — try a text-based PDF instead.")
            st.stop()

        # --- Role prediction with confidence (Feature: confidence score) ---
        try:
            resume_vector = vectorizer.transform([resume_text])
            top_roles = get_top_roles(model, resume_vector, top_n=3)
        except Exception as e:
            st.error(f"Role prediction failed: {e}")
            st.stop()

        predicted_role = top_roles[0][0]

        st.markdown(render_section_header("Top Career Matches", eyebrow="ML · TF-IDF + Logistic Regression"), unsafe_allow_html=True)
        for role, conf in top_roles:
            st.markdown(render_match_bar(role, conf), unsafe_allow_html=True)

        # --- Resume vs JD match score (Feature: match %) ---
        match_score = compute_match_score(resume_text, job_description)
        st.markdown(render_section_header("Resume ↔ Job Description Match", eyebrow="TF-IDF Cosine Similarity"), unsafe_allow_html=True)
        st.markdown(render_match_bar("Content overlap", match_score), unsafe_allow_html=True)

        # --- ATS analysis via Gemini ---
        prompt = f"""
        You are an expert ATS Resume Analyzer.

        Analyze the resume against the given job description.

        Return the response in the following format:

        ATS Score: xx/100

        Resume Summary:
        ...

        Missing Keywords:
        - keyword1
        - keyword2

        Strengths:
        - point1
        - point2

        Weaknesses:
        - point1
        - point2

        Improvement Suggestions:
        - point1
        - point2

        Resume:
        {resume_text}

        Job Description:
        {job_description}
        """

        with st.spinner("Running ATS analysis..."):
            analysis_text = call_gemini(prompt)

        if analysis_text:
            score = extract_ats_score(analysis_text)
            if score is not None:
                st.markdown(render_score_card(score), unsafe_allow_html=True)

            st.markdown(render_section_header("ATS Analysis", eyebrow="Gemini 2.5 Flash"), unsafe_allow_html=True)
            st.write(analysis_text)

            st.download_button(
                label="Download Report (.pdf)",
                data=build_pdf_report(f"ATS Report — {uploaded_file.name}", analysis_text),
                file_name="ats_report.pdf",
                mime="application/pdf",
            )

            # --- Keyword highlighting (Feature) ---
            missing_keywords = extract_section(analysis_text, "Missing Keywords")
            if missing_keywords:
                with st.expander("📌 Resume with missing keywords highlighted"):
                    st.markdown(
                        highlight_keywords_html(resume_text, missing_keywords),
                        unsafe_allow_html=True,
                    )

            # --- Section-wise breakdown (Feature) ---
            with st.expander("🧩 Section-wise resume breakdown"):
                sections = split_resume_sections(resume_text)
                if len(sections) <= 1:
                    st.caption("Couldn't reliably detect section headers in this resume.")
                else:
                    for name, content in sections.items():
                        st.markdown(f"**{name}**")
                        st.text(content[:800] + ("..." if len(content) > 800 else ""))

            # --- Rewrite suggestions (Feature) ---
            weaknesses = extract_section(analysis_text, "Weaknesses")
            if weaknesses:
                if st.button("✍️ Rewrite weak bullet points", key="rewrite_btn"):
                    rewrite_prompt = f"""
                    Given this resume and these identified weaknesses, rewrite 2-3
                    of the weakest resume bullet points into stronger, ATS-friendly
                    versions. Show original vs rewritten, side by side, briefly.

                    Resume:
                    {resume_text}

                    Identified weaknesses:
                    {chr(10).join('- ' + w for w in weaknesses)}
                    """
                    with st.spinner("Rewriting weak points..."):
                        rewritten = call_gemini(rewrite_prompt)
                    if rewritten:
                        st.markdown(render_section_header("Suggested Rewrites", eyebrow="Gemini 2.5 Flash"), unsafe_allow_html=True)
                        st.write(rewritten)

            # Save to session for chat + history tabs
            st.session_state.active_resume = {"text": resume_text, "jd": job_description}
            st.session_state.history.append(
                {
                    "filename": uploaded_file.name,
                    "role": predicted_role,
                    "ats_score": extract_ats_score(analysis_text),
                    "match_score": match_score,
                    "analysis": analysis_text,
                    "resume_text": resume_text,
                    "jd": job_description,
                }
            )
            st.session_state.history = st.session_state.history[-5:]  # keep last 5


# ===========================================================
# TAB 2 — Bulk Compare
# ===========================================================
with tab_bulk:
    st.caption("Upload multiple resumes and compare them against a single job description.")

    bulk_files = st.file_uploader(
        "Upload Resumes (PDF, multiple)", type=["pdf"], accept_multiple_files=True, key="bulk_upload"
    )
    bulk_jd = st.text_area("Paste Job Description", height=200, key="bulk_jd")

    if st.button("Compare Resumes", key="bulk_compare_btn"):

        if not bulk_files:
            st.warning("Please upload at least one resume.")
            st.stop()

        if not bulk_jd or not bulk_jd.strip():
            st.warning("Please enter a Job Description.")
            st.stop()

        results = []
        progress = st.progress(0)

        for i, f in enumerate(bulk_files):
            try:
                if f.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    st.warning(f"Skipped {f.name}: exceeds {MAX_FILE_SIZE_MB} MB.")
                    continue

                text = extract_text_from_pdf(f)
                if not text or not text.strip():
                    st.warning(f"Skipped {f.name}: no extractable text.")
                    continue

                vec = vectorizer.transform([text])
                roles = get_top_roles(model, vec, top_n=1)
                match = compute_match_score(text, bulk_jd)

                results.append(
                    {
                        "filename": f.name,
                        "predicted_role": roles[0][0],
                        "role_confidence": roles[0][1],
                        "match_score": match,
                    }
                )
            except Exception as e:
                st.warning(f"Failed to process {f.name}: {e}")
            finally:
                progress.progress((i + 1) / len(bulk_files))

        if results:
            results.sort(key=lambda r: r["match_score"], reverse=True)
            st.markdown(render_section_header("Ranked Results", eyebrow="Sorted by JD Match"), unsafe_allow_html=True)
            st.table(
                [
                    {
                        "Rank": idx + 1,
                        "File": r["filename"],
                        "Predicted Role": r["predicted_role"],
                        "Role Confidence %": r["role_confidence"],
                        "JD Match %": r["match_score"],
                    }
                    for idx, r in enumerate(results)
                ]
            )
        else:
            st.info("No resumes could be processed.")


# ===========================================================
# TAB 3 — Cover Letter Generator
# ===========================================================
with tab_cover:
    st.caption("Generate a tailored cover letter from a resume + job description.")

    cover_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], key="cover_upload")
    cover_jd = st.text_area("Paste Job Description", height=200, key="cover_jd")
    tone = st.selectbox("Tone", ["Professional", "Enthusiastic", "Concise", "Formal"], key="cover_tone")

    if st.button("Generate Cover Letter", key="cover_btn"):

        if cover_file is None:
            st.warning("Please upload a resume.")
            st.stop()
        if not cover_jd or not cover_jd.strip():
            st.warning("Please enter a Job Description.")
            st.stop()

        try:
            with st.spinner("Reading resume..."):
                cover_resume_text = extract_text_from_pdf(cover_file)
        except Exception as e:
            st.error(f"Failed to extract text from PDF: {e}")
            st.stop()

        if not cover_resume_text or not cover_resume_text.strip():
            st.error("No text could be extracted from this PDF.")
            st.stop()

        cover_prompt = f"""
        Write a {tone.lower()} cover letter (under 350 words) tailored to the
        job description below, based on the candidate's resume. Do not invent
        experience that isn't in the resume. Address it generically
        ("Dear Hiring Manager") since no company name was provided unless one
        appears in the job description.

        Resume:
        {cover_resume_text}

        Job Description:
        {cover_jd}
        """

        with st.spinner("Writing cover letter..."):
            letter = call_gemini(cover_prompt)

        if letter:
            st.markdown(render_section_header("Your Cover Letter", eyebrow="Gemini 2.5 Flash"), unsafe_allow_html=True)
            st.write(letter)
            st.download_button(
                label="Download Cover Letter (.pdf)",
                data=build_pdf_report("Cover Letter", letter),
                file_name="cover_letter.pdf",
                mime="application/pdf",
            )


# ===========================================================
# TAB 4 — Chat with Resume
# ===========================================================
with tab_chat:
    st.caption("Ask follow-up questions about your most recently analyzed resume.")

    if not st.session_state.active_resume:
        st.info("Run an analysis in the **Single Analysis** tab first — this chat uses that resume + job description as context.")
    else:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_q = st.chat_input("Ask something about your resume or the analysis...")

        if user_q:
            st.session_state.chat_messages.append({"role": "user", "content": user_q})
            with st.chat_message("user"):
                st.write(user_q)

            history_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in st.session_state.chat_messages[-6:]
            )

            chat_prompt = f"""
            You are a helpful resume and career advisor. The candidate's resume
            and the job description they're targeting are below. Answer their
            question concisely and specifically, referencing the resume content
            where relevant.

            Resume:
            {st.session_state.active_resume['text']}

            Job Description:
            {st.session_state.active_resume['jd']}

            Conversation so far:
            {history_text}

            Answer the latest user question.
            """

            with st.spinner("Thinking..."):
                reply = call_gemini(chat_prompt)

            if reply:
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                with st.chat_message("assistant"):
                    st.write(reply)

        if st.session_state.chat_messages:
            if st.button("Clear chat", key="clear_chat_btn"):
                st.session_state.chat_messages = []
                st.rerun()


# ===========================================================
# TAB 5 — History
# ===========================================================
with tab_history:
    st.caption("Last 5 analyses from this session (cleared on browser refresh).")

    if not st.session_state.history:
        st.info("No analyses yet. Run one from the Single Analysis tab.")
    else:
        for i, entry in enumerate(reversed(st.session_state.history)):
            label = f"{entry['filename']} — {entry['role']}"
            if entry["ats_score"] is not None:
                label += f" — ATS {entry['ats_score']}/100"
            with st.expander(label):
                st.caption(f"JD match: {entry['match_score']}%")
                st.write(entry["analysis"])
                st.download_button(
                    label="Download this report (.pdf)",
                    data=build_pdf_report(f"ATS Report — {entry['filename']}", entry["analysis"]),
                    file_name=f"ats_report_{i}.pdf",
                    mime="application/pdf",
                    key=f"history_dl_{i}",
                )
