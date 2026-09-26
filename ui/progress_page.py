import streamlit as st

from database import get_db_context
from database.models import (
    InterviewProgress,
    InterviewSession,
    UserSession,
)


def show_progress_page():
    st.title("Progress Tracking")
    st.markdown("Track your interview preparation progress over time")

    with get_db_context() as db:
        session = (
            db.query(UserSession)
            .filter(UserSession.session_id == st.session_state.user_session_id)
            .first()
        )

        if not session:
            st.info("No data yet. Complete an interview to see progress.")
            return

        progress = (
            db.query(InterviewProgress).filter(InterviewProgress.session_id == session.id).first()
        )

        interviews = (
            db.query(InterviewSession)
            .filter(InterviewSession.session_id == session.id)
            .order_by(InterviewSession.created_at)
            .all()
        )

    if not interviews:
        st.info("No interviews yet. Start one from the Interview Setup page.")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = progress.total_interviews if progress else len(interviews)
        st.metric("Total Interviews", total)

    with col2:
        total_questions = (
            progress.total_questions_answered
            if progress
            else sum(i.total_questions or 0 for i in interviews)
        )
        st.metric("Questions Answered", total_questions)

    with col3:
        avg = progress.average_overall_score if progress else 0
        if avg:
            st.metric("Average Score", f"{avg:.1f}/10")
        else:
            st.metric("Average Score", "N/A")

    with col4:
        latest = interviews[-1].overall_score if interviews and interviews[-1].overall_score else 0
        if latest:
            st.metric("Latest Score", f"{latest:.1f}/10")
        else:
            st.metric("Latest Score", "N/A")

    st.markdown("---")

    import pandas as pd
    import plotly.express as px

    rows = []
    for i in interviews:
        rows.append(
            {
                "Date": i.created_at,
                "Overall": float(i.overall_score or 0),
                "Technical": float(i.technical_score or 0),
                "Communication": float(i.communication_score or 0),
                "HR": float(i.hr_score or 0),
                "Problem Solving": float(i.problem_solving_score or 0),
            }
        )

    df = pd.DataFrame(rows)

    st.subheader("Score Trend")
    fig = px.line(
        df,
        x="Date",
        y=["Overall", "Technical", "Communication", "HR", "Problem Solving"],
        title="Scores Over Time",
        markers=True,
    )
    fig.update_layout(height=350, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    if progress and progress.strong_areas:
        st.subheader("Strong Areas")
        st.write(", ".join(str(a) for a in progress.strong_areas))

    if progress and progress.weak_areas:
        st.subheader("Areas to Improve")
        st.write(", ".join(str(a) for a in progress.weak_areas))

    if progress and progress.score_history:
        st.subheader("Score History")
        history = progress.score_history
        if isinstance(history, list):
            hist_df = pd.DataFrame(history)
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
