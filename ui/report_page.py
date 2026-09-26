import json

import streamlit as st

from database import get_db_context
from database.models import InterviewSession

_CATEGORY_LABELS = {
    "technical": "Technical",
    "hr": "HR",
    "behavioral": "Behavioral",
    "situational": "Situational",
    "project_based": "Project-based",
    "project-based": "Project-based",
    "resume_based": "Resume-based",
    "resume-based": "Resume-based",
    "job_specific": "Job-specific",
    "job-specific": "Job-specific",
}


_DIFFICULTY_LABELS = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
}


def _format_category(value):
    if value is None:
        return "N/A"
    if hasattr(value, "value"):
        value = value.value
    return _CATEGORY_LABELS.get(str(value).lower(), str(value).replace("_", "- ").title())


def _format_difficulty(value):
    if value is None:
        return "N/A"
    if hasattr(value, "value"):
        value = value.value
    return _DIFFICULTY_LABELS.get(str(value).lower(), str(value).title())


def show_report_page():
    st.title("📊 Interview Reports")
    st.markdown("View detailed performance reports from your mock interviews")

    from database.models import UserSession

    with get_db_context() as db:
        user_session = (
            db.query(UserSession)
            .filter(UserSession.session_id == st.session_state.user_session_id)
            .first()
        )

        if not user_session:
            st.info("No interview data found.")
            return

        interviews = (
            db.query(InterviewSession)
            .filter(InterviewSession.session_id == user_session.id)
            .order_by(InterviewSession.created_at.desc())
            .all()
        )

    if not interviews:
        st.info("No completed interviews yet. Start an interview to see reports!")
        return

    options = []
    for i in interviews:
        date_str = i.created_at.strftime("%Y-%m-%d %H:%M") if i.created_at else "Unknown"
        label = (
            f"{date_str} - {i.interview_type or 'N/A'} - " f"{i.overall_score:.1f}/10"
            if i.overall_score
            else f"{date_str} - {i.interview_type or 'N/A'} - Incomplete"
        )
        options.append((label, i.id))

    selected = st.selectbox("Select Interview", options, format_func=lambda o: o[0])
    selected_id = selected[1]

    with get_db_context() as db:
        selected_interview = (
            db.query(InterviewSession).filter(InterviewSession.id == selected_id).first()
        )

    if not selected_interview:
        st.error("Selected interview could not be loaded.")
        return

    if selected_interview.status != "completed":
        st.warning("This interview is not completed yet.")
        return

    show_interview_report(selected_interview)


def show_interview_report(interview: InterviewSession):
    st.subheader("📈 Overall Performance")

    col1, col2, col3, col4, col5 = st.columns(5)
    metrics = [
        ("Overall", interview.overall_score, 10),
        ("Technical", interview.technical_score, 10),
        ("Communication", interview.communication_score, 10),
        ("HR/Behavioral", interview.hr_score, 10),
        ("Problem Solving", interview.problem_solving_score, 10),
    ]

    for col, (label, score, max_score) in zip([col1, col2, col3, col4, col5], metrics):
        with col:
            if score:
                score_val = float(score)
                st.metric(label, f"{score_val:.1f}/{max_score}", get_score_label(score_val))
            else:
                st.metric(label, "N/A")

    if all(m[1] for m in metrics):
        show_radar_chart(metrics)

    st.markdown("---")

    tabs = st.tabs(
        [
            "💪 Strengths",
            "⚠️ Weaknesses",
            "🔍 Missed Concepts",
            "📚 Recommended Topics",
            "🚀 Recommended Projects",
            "❓ Practice Questions",
            "📅 7-Day Plan",
            "📅 30-Day Plan",
            "📋 Question Details",
        ]
    )

    with tabs[0]:
        show_list_section("Strengths", interview.strengths)

    with tabs[1]:
        show_list_section("Weaknesses", interview.weaknesses)

    with tabs[2]:
        show_list_section("Frequently Missed Concepts", interview.missed_concepts)

    with tabs[3]:
        show_list_section("Recommended Topics to Study", interview.recommended_topics)

    with tabs[4]:
        show_list_section("Recommended Projects", interview.recommended_projects)

    with tabs[5]:
        show_list_section("Recommended Practice Questions", interview.recommended_questions)

    with tabs[6]:
        show_improvement_plan("7-Day Improvement Plan", interview.improvement_plan_7_day)

    with tabs[7]:
        show_improvement_plan("30-Day Improvement Plan", interview.improvement_plan_30_day)

    with tabs[8]:
        show_question_details(interview.id)

    st.markdown("---")
    report_data = {
        "interview_date": interview.created_at.isoformat(),
        "interview_type": interview.interview_type,
        "difficulty": interview.difficulty,
        "scores": {
            "overall": interview.overall_score,
            "technical": interview.technical_score,
            "communication": interview.communication_score,
            "hr": interview.hr_score,
            "problem_solving": interview.problem_solving_score,
        },
        "strengths": interview.strengths,
        "weaknesses": interview.weaknesses,
        "missed_concepts": interview.missed_concepts,
        "recommended_topics": interview.recommended_topics,
        "recommended_projects": interview.recommended_projects,
        "recommended_questions": interview.recommended_questions,
        "improvement_plan_7_day": interview.improvement_plan_7_day,
        "improvement_plan_30_day": interview.improvement_plan_30_day,
    }

    st.download_button(
        "📥 Download Report (JSON)",
        data=json.dumps(report_data, indent=2),
        file_name=f"interview_report_{interview.created_at.strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        use_container_width=True,
    )


def get_score_label(score: float) -> str:
    if score >= 8.5:
        return "Excellent"
    elif score >= 7:
        return "Good"
    elif score >= 5:
        return "Average"
    else:
        return "Needs Improvement"


def show_radar_chart(metrics):
    import plotly.graph_objects as go

    categories = [m[0] for m in metrics]
    values = [m[1] for m in metrics]
    max_val = max(m[2] for m in metrics)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill="toself", name="Your Scores"))

    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [0, max_val]}},
        showlegend=False,
        height=400,
        title="Skill Radar",
    )

    st.plotly_chart(fig, use_container_width=True)


def show_list_section(title, items):
    if items:
        for item in items:
            st.write(f"• {item}")
    else:
        st.info(f"No {title.lower()} recorded")


def show_improvement_plan(title, plan):
    if plan:
        for item in plan:
            if isinstance(item, dict):
                with st.expander(f"Day {item.get('day', '?')}: {item.get('focus', 'Focus')}"):
                    st.write(f"**Activity:** {item.get('activity', 'N/A')}")
                    st.write(f"**Estimated Hours:** {item.get('estimated_hours', 'N/A')}")
                    if item.get("resources"):
                        st.write("**Resources:**")
                        for res in item["resources"]:
                            st.write(f"• {res}")
    else:
        st.info(f"No {title} available")


def show_question_details(interview_id):
    with get_db_context() as db:
        from database.models import InterviewQuestion

        questions = (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.interview_session_id == interview_id)
            .order_by(InterviewQuestion.question_number)
            .all()
        )

    for q in questions:
        category_label = _format_category(q.category)
        difficulty_label = _format_difficulty(q.difficulty)
        with st.expander(f"Q{q.question_number}: {category_label} ({difficulty_label})"):
            st.write(f"**Question:** {q.question_text}")
            st.write(
                f"**Expected Points:** {', '.join(q.expected_key_points) if q.expected_key_points else 'N/A'}"
            )

            if q.answer_text:
                st.write(f"**Your Answer:** {q.answer_text}")

                if q.overall_score:
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("Technical", f"{q.technical_accuracy:.1f}/10")
                    with col2:
                        st.metric("Relevance", f"{q.relevance:.1f}/10")
                    with col3:
                        st.metric("Communication", f"{q.communication:.1f}/10")
                    with col4:
                        st.metric("Confidence", f"{q.confidence:.1f}/10")
                    with col5:
                        st.metric("Completeness", f"{q.completeness:.1f}/10")

                    st.metric("Overall", f"{q.overall_score:.1f}/10")

                    st.write(f"**Strengths:** {', '.join(q.strengths) if q.strengths else 'N/A'}")
                    st.write(
                        f"**Weaknesses:** {', '.join(q.weaknesses) if q.weaknesses else 'N/A'}"
                    )
                    st.write(
                        f"**Missing:** {', '.join(q.missing_points) if q.missing_points else 'N/A'}"
                    )
                    st.write(
                        f"**Better Answer:** {q.suggested_answer if q.suggested_answer else 'N/A'}"
                    )
            else:
                st.info("Not answered")
