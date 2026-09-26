import streamlit as st

from config.settings import settings
from database import get_db_context
from database.models import JobDescription, ResumeAnalysis, ResumeJobMatch, UserSession
from rag import create_retriever, create_text_splitter, load_document
from services import (
    JobAnalysisResult,
    ResumeJobMatchResult,
    analyze_job_description,
    match_resume_job,
)
from utils.file_utils import (
    save_uploaded_file,
    validate_file_extension,
    validate_file_size,
)


def show_job_page():
    st.title("Job Matcher")
    st.markdown("Analyze job descriptions and match against your resume")

    if "resume_analysis" not in st.session_state:
        st.warning("Please analyze your resume first!")
        if st.button("Go to Resume Analyzer", use_container_width=True):
            st.session_state.current_page = "resume"
            st.rerun()
        return

    tab1, tab2 = st.tabs(["Paste Job Description", "Upload File"])

    job_text = st.session_state.get("job_text", "")
    job_file_path = st.session_state.get("job_file_path")
    job_source = st.session_state.get("job_source", "pasted")

    with tab1:
        job_text = st.text_area(
            "Paste Job Description Here",
            height=300,
            placeholder="Paste the full job description including requirements, responsibilities, qualifications, etc.",
            value=job_text,
        )

    with tab2:
        uploaded_file = st.file_uploader(
            "Upload Job Description (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            key="job_upload",
        )

        if uploaded_file:
            if not validate_file_extension(uploaded_file.name):
                st.error("Invalid file type. Please upload PDF, DOCX, or TXT.")
            else:
                file_path, safe_name = save_uploaded_file(uploaded_file)

                if not validate_file_size(file_path):
                    st.error(f"File too large. Max size: {settings.max_file_size_mb}MB")
                else:
                    documents = load_document(file_path)
                    job_text = "\n\n".join([d.content for d in documents])
                    job_file_path = file_path
                    job_source = safe_name
                    st.success(f"File uploaded: {safe_name}")

                    with st.expander("Extracted Text Preview"):
                        st.text_area(
                            "",
                            job_text[:3000] + ("..." if len(job_text) > 3000 else ""),
                            height=200,
                        )

    if job_text and job_text.strip():
        if st.button("Analyze Job Description", type="primary", use_container_width=True):
            with st.spinner("Analyzing job description..."):
                try:
                    job_analysis = analyze_job_description(job_text)

                    st.session_state.job_analysis = job_analysis
                    st.session_state.job_text = job_text
                    st.session_state.job_file_path = job_file_path
                    st.session_state.job_source = job_source

                    try:
                        save_job_to_db(
                            job_analysis,
                            job_text,
                            job_source,
                        )
                    except Exception as db_error:
                        st.warning(f"Job analysis succeeded, but database save failed: {db_error}")

                    try:
                        add_job_to_rag(job_text, job_source)
                    except Exception as rag_error:
                        st.warning(f"Job analysis succeeded, but RAG indexing failed: {rag_error}")

                    st.success("Job description analyzed!")
                    st.rerun()

                except Exception as e:
                    msg = str(e)
                    if "API key not provided" in msg or "not authenticated" in msg.lower():
                        st.error(
                            "API key not configured or invalid. Please enter your API key in **Settings**."
                        )
                    elif "HTTP 429" in msg or "rate limit" in msg.lower():
                        st.error("Rate limit exceeded. Please wait a moment and try again.")
                    elif "HTTP 40" in msg:
                        st.error(f"API request failed: {msg}")
                    else:
                        st.error(f"Analysis failed: {msg}")

    if "job_analysis" in st.session_state:
        show_job_results()

        st.markdown("---")
        if st.button("Match Resume with Job", type="primary", use_container_width=True):
            with st.spinner("Matching resume with job description..."):
                try:
                    match_result = match_resume_job(
                        st.session_state.resume_analysis, st.session_state.job_analysis
                    )

                    st.session_state.match_analysis = match_result
                    save_match_to_db(match_result)

                    st.success("Match analysis complete!")
                    st.rerun()

                except Exception as e:
                    msg = str(e)
                    if "API key not provided" in msg or "not authenticated" in msg.lower():
                        st.error(
                            "API key not configured or invalid. Please enter your API key in **Settings**."
                        )
                    elif "HTTP 429" in msg or "rate limit" in msg.lower():
                        st.error("Rate limit exceeded. Please wait a moment and try again.")
                    elif "HTTP 40" in msg:
                        st.error(f"API request failed: {msg}")
                    else:
                        st.error(f"Matching failed: {msg}")

        if "match_analysis" in st.session_state:
            show_match_results()


def show_job_results():
    job: JobAnalysisResult = st.session_state.job_analysis

    st.markdown("---")
    st.subheader("📋 Job Analysis Results")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Job Title:**", job.job_title or "Not specified")
        st.write("**Company:**", job.company or "Not specified")

    with col2:
        st.write("**Experience Required:**")
        for exp in job.experience_requirements:
            st.write(f"• {exp}")

    tabs = st.tabs(
        [
            "Required Skills",
            "Preferred Skills",
            "Tech Stack",
            "Responsibilities",
            "Keywords",
        ]
    )

    with tabs[0]:
        if job.required_skills:
            for skill in job.required_skills:
                st.write(f"🔴 {skill}")
        else:
            st.info("None specified")

    with tabs[1]:
        if job.preferred_skills:
            for skill in job.preferred_skills:
                st.write(f"🟡 {skill}")
        else:
            st.info("None specified")

    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.write(
                "**Languages:**",
                (", ".join(job.programming_languages) if job.programming_languages else "None"),
            )
            st.write("**Frameworks:**", ", ".join(job.frameworks) if job.frameworks else "None")
        with col2:
            st.write("**Databases:**", ", ".join(job.databases) if job.databases else "None")
            st.write("**Tools:**", ", ".join(job.tools) if job.tools else "None")

    with tabs[3]:
        if job.responsibilities:
            for resp in job.responsibilities:
                st.write(f"• {resp}")
        else:
            st.info("None specified")

    with tabs[4]:
        if job.keywords:
            st.write(", ".join(job.keywords))
        else:
            st.info("None extracted")


def show_match_results():
    match: ResumeJobMatchResult = st.session_state.match_analysis

    st.markdown("---")
    st.subheader("🔗 Resume-Job Match Results")

    col1, col2, col3, col4, col5 = st.columns(5)

    score_data = [
        ("Technical", match.technical_skills_match),
        ("Experience", match.experience_match),
        ("Projects", match.projects_match),
        ("Education", match.education_match),
        ("Overall", match.overall_match),
    ]

    for col, (label, score) in zip([col1, col2, col3, col4, col5], score_data):
        with col:
            delta_color = "normal" if score >= 70 else "inverse"
            st.metric(
                label,
                f"{score:.0f}%",
                delta=get_match_category(score),
                delta_color=delta_color,
            )

    if match.matching_skills:
        st.write("**✅ Matching Skills:**")
        for skill in match.matching_skills:
            with st.expander(f"{skill.skill} ({skill.match_strength})"):
                st.write(f"**Resume Evidence:** {skill.resume_evidence}")
                st.write(f"**Job Requirement:** {skill.job_requirement}")

    if match.missing_skills:
        st.write("**❌ Missing Skills:**")
        for skill in match.missing_skills:
            with st.expander(f"{skill.skill} ({skill.importance})"):
                st.write(f"**Job Requirement:** {skill.job_requirement}")
                if skill.learning_resources:
                    st.write("**Learning Resources:**")
                    for res in skill.learning_resources:
                        st.write(f"• {res}")

    if match.skill_gaps:
        st.write("**🔍 Skill Gaps:**")
        for gap in match.skill_gaps:
            st.write(f"• {gap}")

    if match.experience_gaps:
        st.write("**📉 Experience Gaps:**")
        for gap in match.experience_gaps:
            with st.expander(f"{gap.area}"):
                st.write(f"**Job Requirement:** {gap.job_requirement}")
                st.write(f"**Your Status:** {gap.resume_status}")
                st.write(f"**Gap:** {gap.gap_description}")

    if match.recommendations:
        st.write("**💡 Recommendations:**")
        for rec in match.recommendations:
            st.write(f"• {rec}")

    st.markdown("---")
    if st.button("🤖 Setup Interview", type="primary", use_container_width=True):
        st.session_state.current_page = "interview_setup"
        st.rerun()


def get_match_category(score: float) -> str:
    if score >= 80:
        return "Strong Match"
    elif score >= 60:
        return "Good Match"
    elif score >= 40:
        return "Partial Match"
    else:
        return "Weak Match"


def save_job_to_db(job: JobAnalysisResult, raw_text: str, source: str):
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

        job_desc = JobDescription(
            session_id=session.id,
            title=job.job_title,
            company=job.company,
            raw_text=raw_text,
            source=source,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
            programming_languages=job.programming_languages,
            frameworks=job.frameworks,
            databases=job.databases,
            tools=job.tools,
            experience_requirements=job.experience_requirements,
            education_requirements=job.education_requirements,
            responsibilities=job.responsibilities,
            keywords=job.keywords,
        )

        db.add(job_desc)


def add_job_to_rag(job_text: str, source: str):
    splitter = create_text_splitter()
    chunks = splitter.split_text(job_text, metadata={"type": "job_description"}, source=source)

    retriever = create_retriever()
    retriever.add_documents(chunks)


def save_match_to_db(match: ResumeJobMatchResult):
    with get_db_context() as db:
        user_session = (
            db.query(UserSession)
            .filter(UserSession.session_id == st.session_state.user_session_id)
            .first()
        )
        assert user_session is not None

        resume = (
            db.query(ResumeAnalysis).filter(ResumeAnalysis.session_id == user_session.id).first()
        )

        job = db.query(JobDescription).filter(JobDescription.session_id == user_session.id).first()

        if resume and job:
            match_record = ResumeJobMatch(
                resume_analysis_id=resume.id,
                job_description_id=job.id,
                technical_skills_match=match.technical_skills_match,
                experience_match=match.experience_match,
                projects_match=match.projects_match,
                education_match=match.education_match,
                overall_match=match.overall_match,
                matching_skills=[s.model_dump() for s in match.matching_skills],
                missing_skills=[s.model_dump() for s in match.missing_skills],
                skill_gaps=match.skill_gaps,
                experience_gaps=[g.model_dump() for g in match.experience_gaps],
                recommendations=match.recommendations,
            )

            db.add(match_record)
