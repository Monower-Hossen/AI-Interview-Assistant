import json

import streamlit as st

from config.settings import settings
from database import get_db_context
from database.models import ResumeAnalysis, UserSession
from rag import (
    create_retriever,
    create_text_splitter,
    load_document,
)
from services import ResumeAnalysisResult, ResumeScores, analyze_resume
from utils.file_utils import (
    compute_file_hash,
    save_uploaded_file,
    validate_file_extension,
    validate_file_size,
)


def show_resume_page():
    st.title("Resume Analyzer")
    st.markdown("Upload your resume for AI-powered analysis and scoring")

    uploaded_file = st.file_uploader(
        "Upload Resume (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        help=f"Max file size: {settings.max_file_size_mb}MB",
        key="resume_upload",
    )

    if uploaded_file:
        if not validate_file_extension(uploaded_file.name):
            st.error("Invalid file type. Please upload PDF, DOCX, or TXT.")
            return

        file_path, safe_name = save_uploaded_file(uploaded_file)

        if not validate_file_size(file_path):
            st.error(f"File too large. Max size: {settings.max_file_size_mb}MB")
            return

        st.success(f"File uploaded: {safe_name}")

        with st.spinner("Extracting text from resume..."):
            documents = load_document(file_path)
            resume_text = "\n\n".join([d.content for d in documents])

        if not resume_text.strip():
            st.error("Could not extract text from the file.")
            return

        with st.expander("Extracted Text Preview"):
            st.text_area(
                "Extracted Text",
                resume_text[:3000] + ("..." if len(resume_text) > 3000 else ""),
                height=200,
                label_visibility="collapsed",
            )

        if st.button("Analyze Resume", type="primary", use_container_width=True):
            with st.spinner("Analyzing resume with AI..."):
                try:
                    analysis, scores = analyze_resume(resume_text)

                    st.session_state.resume_analysis = analysis
                    st.session_state.resume_scores = scores
                    st.session_state.resume_text = resume_text
                    st.session_state.resume_file_path = file_path
                    st.session_state.resume_file_hash = compute_file_hash(file_path)
                    st.session_state.resume_shown_empty_warning = False

                    try:
                        save_resume_to_db(analysis, scores, safe_name, file_path, resume_text)
                    except Exception as db_error:
                        st.warning(f"Analysis succeeded, but database save failed: {db_error}")

                    try:
                        add_resume_to_rag(resume_text, file_path)
                    except Exception as rag_error:
                        st.warning(f"Analysis succeeded, but RAG indexing failed: {rag_error}")
                    st.rerun()

                except Exception as e:
                    msg = str(e)

                    if "API key not provided" in msg or "not authenticated" in msg.lower():
                        st.error("API key is missing or invalid. Check LLM_API_KEY in your .env.")
                    elif "HTTP 429" in msg or "rate limit" in msg.lower():
                        st.error("Rate limit reached. Wait a little and try again.")
                    elif "timeout" in msg.lower() or "timed out" in msg.lower():
                        st.error("The AI request timed out. Check your internet connection.")
                    elif "WinError 10054" in msg or "connection" in msg.lower():
                        st.error("The AI connection was reset. Check internet/API status.")
                    else:
                        st.error(f"Resume analysis failed: {msg}")

    if "resume_analysis" in st.session_state:
        _analysis = st.session_state.resume_analysis
        _scores = st.session_state.resume_scores
        _is_empty = (
            _scores.overall == 0
            and _scores.technical_skills == 0
            and _scores.experience == 0
            and _scores.projects == 0
            and _scores.education == 0
            and _scores.certifications == 0
            and _scores.structure == 0
            and not _analysis.candidate_name
            and not _analysis.email
            and not _analysis.skills
        )
        if _is_empty and not st.session_state.get("resume_shown_empty_warning", False):
            st.warning(
                "Resume analysis returned no results. "
                "This usually means LLM providers are not working. "
                "Check your API keys in Settings, or run a connection test."
            )
            st.session_state.resume_shown_empty_warning = True
        show_resume_results()


def show_resume_results():
    analysis: ResumeAnalysisResult = st.session_state.resume_analysis
    scores: ResumeScores = st.session_state.resume_scores

    st.markdown("---")
    st.subheader("📊 Analysis Results")

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    score_data = [
        ("Technical", scores.technical_skills),
        ("Experience", scores.experience),
        ("Projects", scores.projects),
        ("Education", scores.education),
        ("Certs", scores.certifications),
        ("Structure", scores.structure),
        ("Overall", scores.overall),
    ]

    for col, (label, score) in zip([col1, col2, col3, col4, col5, col6, col7], score_data):
        with col:
            delta_color = "normal" if score >= 70 else "inverse"
            st.metric(
                label,
                f"{score:.0f}",
                delta=get_score_category(score),
                delta_color=delta_color,
            )

    tabs = st.tabs(
        [
            "👤 Profile",
            "🎓 Education",
            "💼 Experience",
            "🛠️ Skills",
            "🚀 Projects",
            "📜 Certifications",
            "💪 Strengths/Weaknesses",
        ]
    )

    with tabs[0]:
        show_profile_section(analysis)

    with tabs[1]:
        show_education_section(analysis)

    with tabs[2]:
        show_experience_section(analysis)

    with tabs[3]:
        show_skills_section(analysis)

    with tabs[4]:
        show_projects_section(analysis)

    with tabs[5]:
        show_certifications_section(analysis)

    with tabs[6]:
        show_strengths_weaknesses(analysis)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        export_data = {
            "analysis": analysis.model_dump(),
            "scores": scores.model_dump(),
        }
        st.download_button(
            "📥 Download Analysis (JSON)",
            data=json.dumps(export_data, indent=2),
            file_name="resume_analysis.json",
            mime="application/json",
            use_container_width=True,
        )

    with col2:
        if st.button("🎯 Match with Job Description", use_container_width=True):
            st.session_state.current_page = "job"
            st.rerun()


def show_profile_section(analysis: ResumeAnalysisResult):
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Name:**", analysis.candidate_name or "Not found")
        st.write("**Email:**", analysis.email or "Not found")
        st.write("**Phone:**", analysis.phone or "Not found")

    with col2:
        st.write("**LinkedIn:**", analysis.linkedin or "Not found")
        st.write("**GitHub:**", analysis.github or "Not found")
        st.write("**Portfolio:**", analysis.portfolio or "Not found")


def show_education_section(analysis: ResumeAnalysisResult):
    if analysis.education:
        for edu in analysis.education:
            with st.expander(f"{edu.degree} - {edu.institution}"):
                if edu.year:
                    st.write(f"**Year:** {edu.year}")
                if edu.grade:
                    st.write(f"**Grade:** {edu.grade}")
                if edu.details:
                    st.write(f"**Details:** {edu.details}")
    else:
        st.info("No education information found")


def show_experience_section(analysis: ResumeAnalysisResult):
    if analysis.experience:
        for exp in analysis.experience:
            with st.expander(f"{exp.title} at {exp.company}"):
                if exp.duration:
                    st.write(f"**Duration:** {exp.duration}")
                if exp.description:
                    st.write(f"**Description:** {exp.description}")
                if exp.technologies:
                    st.write(f"**Technologies:** {', '.join(exp.technologies)}")
    else:
        st.info("No work experience found")


def show_skills_section(analysis: ResumeAnalysisResult):
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Programming Languages:**")
        st.write(
            ", ".join(analysis.programming_languages) if analysis.programming_languages else "None"
        )

        st.write("**Frameworks:**")
        st.write(", ".join(analysis.frameworks) if analysis.frameworks else "None")

    with col2:
        st.write("**Databases:**")
        st.write(", ".join(analysis.databases) if analysis.databases else "None")

        st.write("**Tools:**")
        st.write(", ".join(analysis.tools) if analysis.tools else "None")

    st.write("**All Skills:**")
    st.write(", ".join(analysis.skills) if analysis.skills else "None")


def show_projects_section(analysis: ResumeAnalysisResult):
    if analysis.projects:
        for proj in analysis.projects:
            with st.expander(proj.name):
                st.write(f"**Description:** {proj.description}")
                if proj.technologies:
                    st.write(f"**Technologies:** {', '.join(proj.technologies)}")
                if proj.role:
                    st.write(f"**Role:** {proj.role}")
                if proj.duration:
                    st.write(f"**Duration:** {proj.duration}")
    else:
        st.info("No projects found")


def show_certifications_section(analysis: ResumeAnalysisResult):
    if analysis.certifications:
        for cert in analysis.certifications:
            st.write(f"• {cert}")
    else:
        st.info("No certifications found")


def show_strengths_weaknesses(analysis: ResumeAnalysisResult):
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Strengths:**")
        if analysis.strengths:
            for s in analysis.strengths:
                st.write(f"✅ {s}")
        else:
            st.info("None identified")

    with col2:
        st.write("**Weaknesses:**")
        if analysis.weaknesses:
            for w in analysis.weaknesses:
                st.write(f"⚠️ {w}")
        else:
            st.info("None identified")


def get_score_category(score: float) -> str:
    if score >= 90:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Average"
    else:
        return "Needs Work"


def save_resume_to_db(
    analysis: ResumeAnalysisResult,
    scores: ResumeScores,
    file_name: str,
    file_path: str,
    raw_text: str,
):
    with get_db_context() as db:
        session = (
            db.query(UserSession)
            .filter(UserSession.session_id == st.session_state.user_session_id)
            .first()
        )

        if not session:
            session = UserSession(session_id=st.session_state.user_session_id)
            db.add(session)
            db.flush()

        resume = ResumeAnalysis(
            session_id=session.id,
            file_name=file_name,
            file_path=file_path,
            raw_text=raw_text,
            candidate_name=analysis.candidate_name,
            email=analysis.email,
            phone=analysis.phone,
            linkedin=analysis.linkedin,
            github=analysis.github,
            portfolio=analysis.portfolio,
            education=[e.model_dump() for e in analysis.education],
            experience=[e.model_dump() for e in analysis.experience],
            skills=analysis.skills,
            programming_languages=analysis.programming_languages,
            frameworks=analysis.frameworks,
            databases=analysis.databases,
            tools=analysis.tools,
            projects=[p.model_dump() for p in analysis.projects],
            certifications=analysis.certifications,
            strengths=analysis.strengths,
            weaknesses=analysis.weaknesses,
            technical_skills_score=scores.technical_skills,
            experience_score=scores.experience,
            projects_score=scores.projects,
            education_score=scores.education,
            certifications_score=scores.certifications,
            structure_score=scores.structure,
            overall_resume_score=scores.overall,
        )

        db.add(resume)


def add_resume_to_rag(resume_text: str, source: str):
    splitter = create_text_splitter()
    chunks = splitter.split_text(resume_text, metadata={"type": "resume"}, source=source)

    retriever = create_retriever()
    retriever.add_documents(chunks)
