import asyncio
import logging
import os
import sys
import warnings
from pathlib import Path

import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*torchvision.*")

if sys.platform == "win32":

    def _suppress_win32_connection_reset(loop, context):
        exc = context.get("exception")
        if isinstance(exc, ConnectionResetError) and exc.winerror == 10054:
            return
        loop.default_exception_handler(context)

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from database import init_database
from services.llm_service import check_provider_health
from ui.dashboard import show_dashboard
from ui.interview_page import show_interview_page
from ui.job_page import show_job_page
from ui.report_page import show_report_page
from ui.resume_page import show_resume_page
from ui.settings_page import show_settings_page


def main():
    st.set_page_config(
        page_title="AI Interview Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "db_initialized" not in st.session_state:
        init_database()
        st.session_state.db_initialized = True

    if "user_session_id" not in st.session_state:
        import uuid

        st.session_state.user_session_id = str(uuid.uuid4())[:8]

    st.sidebar.title("🤖 AI Interview Assistant")
    st.sidebar.markdown("---")

    pages = {
        "🏠 Dashboard": "dashboard",
        "📄 Resume Analyzer": "resume",
        "🎯 Job Matcher": "job",
        "🤖 Interview Setup": "interview_setup",
        "🎤 Mock Interview": "interview",
        "📊 Interview Report": "report",
        "📈 Progress Tracking": "progress",
        "⚙️ Settings": "settings",
    }

    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"

    for label, key in pages.items():
        if st.sidebar.button(
            label,
            use_container_width=True,
            type="primary" if st.session_state.current_page == key else "secondary",
        ):
            st.session_state.current_page = key
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Session: {st.session_state.user_session_id}")
    _provider = os.environ.get("LLM_PROVIDER", settings.llm_provider).lower()
    _configured = []
    _models = []
    if os.environ.get("GEMINI_API_KEY", settings.gemini_api_key):
        _configured.append("gemini")
        _models.append(os.environ.get("GEMINI_MODEL", settings.gemini_model))
    if os.environ.get("MISTRAL_API_KEY", settings.mistral_api_key):
        _configured.append("mistral")
        _models.append(os.environ.get("MISTRAL_MODEL", settings.mistral_model))
    if os.environ.get("GROQ_API_KEY", settings.groq_api_key):
        _configured.append("groq")
        _models.append(os.environ.get("GROQ_MODEL", settings.groq_model))

    st.sidebar.caption(
        f"Provider: {os.environ.get('LLM_PROVIDER', settings.llm_provider).upper()} | "
        f"Models: {', '.join(_models) if _models else 'none'}"
    )

    if not _configured:
        st.sidebar.warning("⚠️ No API keys configured. Set them in **Settings**.")
    else:
        _status = f"Providers ready: {', '.join(_configured)}"
        if _provider == "auto":
            _status = f"Auto: {', '.join(_configured)} · Using: {_status}"
        st.sidebar.caption(_status)

    if st.sidebar.button("🔍 Check Provider Health"):
        with st.spinner("Checking providers..."):
            _health = check_provider_health()
            for _name, _info in _health.items():
                if _info["healthy"]:
                    st.sidebar.success(f"🟢 {_name}: OK ({_info['model']})")
                else:
                    _err = _info["error"]
                    if _err and len(_err) > 100:
                        _err = _err[:100] + "..."
                    st.sidebar.warning(f"🟡 {_name}: {_err}")
        st.rerun()

    st.sidebar.markdown("---")

    page = st.session_state.current_page

    if page == "dashboard":
        show_dashboard()
    elif page == "resume":
        show_resume_page()
    elif page == "job":
        show_job_page()
    elif page == "interview_setup":
        show_interview_setup()
    elif page == "interview":
        show_interview_page()
    elif page == "report":
        show_report_page()
    elif page == "progress":
        show_progress_page()
    elif page == "settings":
        show_settings_page()


def show_interview_setup():
    st.title("🤖 Interview Setup")
    st.markdown("Configure your mock interview session")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Interview Configuration")

        interview_type = st.selectbox(
            "Interview Type",
            ["Full Interview", "Technical Only", "HR Only", "Behavioral Only", "Mixed"],
            index=0,
        )

        difficulty = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"], index=1)

        num_questions = st.slider("Number of Questions", min_value=5, max_value=15, value=5, step=1)

        categories = st.multiselect(
            "Question Categories",
            [
                "Technical",
                "HR",
                "Behavioral",
                "Situational",
                "Project-based",
                "Resume-based",
                "Job-specific",
            ],
            default=[
                "Technical",
                "HR",
                "Behavioral",
                "Situational",
                "Project-based",
                "Resume-based",
                "Job-specific",
            ],
        )

    with col2:
        st.subheader("Prerequisites Check")

        if "resume_analysis" in st.session_state:
            st.success("✅ Resume analyzed")
            st.caption(f"Candidate: {st.session_state.resume_analysis.candidate_name or 'Unknown'}")
        else:
            st.warning("⚠️ Resume not analyzed yet")

        if "job_analysis" in st.session_state:
            st.success("✅ Job description analyzed")
            st.caption(f"Role: {st.session_state.job_analysis.job_title or 'Unknown'}")
        else:
            st.warning("⚠️ Job description not analyzed yet")

        if "match_analysis" in st.session_state:
            st.success("✅ Resume-Job match completed")
            st.caption(f"Overall Match: {st.session_state.match_analysis.overall_match:.1f}%")
        else:
            st.warning("⚠️ Resume-Job match not done yet")

    st.markdown("---")

    can_generate = (
        "resume_analysis" in st.session_state
        and "job_analysis" in st.session_state
        and "match_analysis" in st.session_state
    )

    if st.button(
        "🚀 Generate Interview Questions",
        type="primary",
        disabled=not can_generate,
        use_container_width=True,
    ):
        if can_generate:
            with st.spinner("Generating personalized interview questions..."):
                from services import (
                    QuestionCategory,
                    generate_interview_questions,
                )

                category_enums = [QuestionCategory(c.lower().replace("-", "_")) for c in categories]
                questions = generate_interview_questions(
                    resume=st.session_state.resume_analysis,
                    job=st.session_state.job_analysis,
                    match=st.session_state.match_analysis,
                    total_questions=num_questions,
                    difficulty=difficulty.lower(),
                    categories=category_enums,
                )

                st.session_state.interview_questions = questions.questions
                st.session_state.interview_config = {
                    "type": interview_type,
                    "difficulty": difficulty,
                    "num_questions": num_questions,
                    "categories": categories,
                }

                st.success(f"✅ Generated {len(questions.questions)} questions!")
                st.rerun()
        else:
            st.error("Please complete resume analysis, job analysis, and matching first.")

    if "interview_questions" in st.session_state:
        st.markdown("---")
        st.subheader("Generated Questions Preview")

        for i, q in enumerate(st.session_state.interview_questions):
            with st.expander(f"Q{i+1}: {q.category.value.title()} ({q.difficulty.value})"):
                st.write(q.question_text)
                st.caption("Expected key points: " + ", ".join(q.expected_key_points))

        if st.button("▶️ Start Mock Interview", type="primary", use_container_width=True):
            st.session_state.current_page = "interview"
            st.session_state.interview_started = True
            st.session_state.current_question_index = 0
            st.session_state.interview_answers = []
            st.session_state.interview_evaluations = []
            st.rerun()


def show_progress_page():
    from ui.progress_page import show_progress_page as _show

    _show()


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(_suppress_win32_connection_reset)
        except RuntimeError:
            pass

    main()
