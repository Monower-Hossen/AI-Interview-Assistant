import pandas as pd
import plotly.express as px
import streamlit as st

from database import get_db_context
from database.models import (
    InterviewProgress,
    InterviewSession,
    ResumeAnalysis,
    UserSession,
)


def _safe_metric(label, value, max_value=100, suffix=""):
    if value is None:
        st.metric(label, "N/A")
    else:
        try:
            st.metric(label, f"{float(value):.1f}/{max_value}{suffix}")
        except (TypeError, ValueError):
            st.metric(label, "N/A")


def show_dashboard():
    st.title("Dashboard")
    st.markdown("Your interview preparation overview")

    with get_db_context() as db:
        session = (
            db.query(UserSession)
            .filter(UserSession.session_id == st.session_state.user_session_id)
            .first()
        )

        if not session:
            st.info("No data yet. Start by analyzing your resume!")
            return

        resume = (
            db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.session_id == session.id)
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )

        interviews = (
            db.query(InterviewSession)
            .filter(InterviewSession.session_id == session.id)
            .order_by(InterviewSession.created_at.desc())
            .all()
        )

        progress = (
            db.query(InterviewProgress).filter(InterviewProgress.session_id == session.id).first()
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        resume_score = resume.overall_resume_score if resume else 0
        if resume_score:
            st.metric("Resume Score", f"{resume_score:.0f}/100")
        else:
            st.metric("Resume Score", "N/A")

    with col2:
        match_score = 0
        if resume:
            from database.models import ResumeJobMatch

            with get_db_context() as db:
                match = (
                    db.query(ResumeJobMatch)
                    .filter(ResumeJobMatch.resume_analysis_id == resume.id)
                    .first()
                )
                if match:
                    match_score = match.overall_match
        if match_score:
            st.metric("Job Match", f"{match_score:.0f}%")
        else:
            st.metric("Job Match", "N/A")

    with col3:
        latest_interview = interviews[0] if interviews else None
        latest_score = latest_interview.overall_score if latest_interview else 0
        if latest_score:
            st.metric("Latest Interview", f"{latest_score:.1f}/10")
        else:
            st.metric("Latest Interview", "N/A")

    with col4:
        avg_score = progress.average_overall_score if progress else 0
        total_interviews = progress.total_interviews if progress else 0
        if avg_score:
            st.metric("Avg Score", f"{avg_score:.1f}/10")
            st.caption(f"{total_interviews} interviews")
        else:
            st.metric("Avg Score", "N/A")
            st.caption(f"{total_interviews} interviews")

    st.markdown("---")

    if interviews:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Interview Score Trend")
            df = pd.DataFrame(
                [
                    {
                        "Date": i.created_at,
                        "Overall": float(i.overall_score or 0),
                        "Technical": float(i.technical_score or 0),
                        "Communication": float(i.communication_score or 0),
                        "HR": float(i.hr_score or 0),
                    }
                    for i in reversed(interviews)
                ]
            )

            fig = px.line(
                df,
                x="Date",
                y=["Overall", "Technical", "Communication", "HR"],
                title="Interview Scores Over Time",
                markers=True,
            )
            fig.update_layout(height=350, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Score Distribution")
            scores = [float(i.overall_score) for i in interviews if i.overall_score]
            if scores:
                fig = px.histogram(
                    x=scores,
                    nbins=10,
                    title="Overall Score Distribution",
                    labels={"x": "Score", "y": "Count"},
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

    if resume and progress and progress.skill_gaps:
        st.subheader("Top Skill Gaps")
        gaps = progress.skill_gaps[:10] if isinstance(progress.skill_gaps, list) else []
        if gaps:
            gap_df = pd.DataFrame(gaps)
            if not gap_df.empty:
                if "skill" not in gap_df.columns and len(gap_df.columns) == 1:
                    gap_df = gap_df.rename(columns={gap_df.columns[0]: "skill"})
                if "skill" in gap_df.columns:
                    y_col = "gap_score" if "gap_score" in gap_df.columns else None
                    fig = px.bar(
                        gap_df.head(10),
                        x="skill",
                        y=y_col,
                        title="Skill Gaps to Address",
                    )
                    st.plotly_chart(fig, use_container_width=True)

    if interviews:
        st.subheader("Recent Interviews")
        interview_data = []
        for i in interviews[:10]:
            interview_data.append(
                {
                    "Date": i.created_at.strftime("%Y-%m-%d %H:%M"),
                    "Type": i.interview_type or "N/A",
                    "Questions": i.total_questions or 0,
                    "Overall": (f"{i.overall_score:.1f}/10" if i.overall_score else "N/A"),
                    "Technical": (f"{i.technical_score:.1f}/10" if i.technical_score else "N/A"),
                    "Communication": (
                        f"{i.communication_score:.1f}/10" if i.communication_score else "N/A"
                    ),
                    "Status": i.status or "N/A",
                }
            )

        df = pd.DataFrame(interview_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Quick Actions")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Analyze Resume", use_container_width=True):
            st.session_state.current_page = "resume"
            st.rerun()

    with col2:
        if st.button("Match with Job", use_container_width=True):
            st.session_state.current_page = "job"
            st.rerun()

    with col3:
        if st.button("Setup Interview", use_container_width=True):
            st.session_state.current_page = "interview_setup"
            st.rerun()

    with col4:
        if st.button("View Reports", use_container_width=True):
            st.session_state.current_page = "report"
            st.rerun()
