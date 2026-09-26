import os
import time
from datetime import datetime

import streamlit as st

from database import get_db_context
from database.models import (
    InterviewQuestion,
    InterviewSession,
    JobDescription,
    ResumeAnalysis,
    UserSession,
)
from services import (
    evaluate_answer,
    generate_interview_report,
)
from services.speech_to_text import transcribe_audio


def show_interview_page():
    st.title("🎤 Mock Interview")
    st.markdown("Practice your interview with AI-powered evaluation")

    if "answer_mode" not in st.session_state:
        st.session_state.answer_mode = "text"
    if "show_evaluation" not in st.session_state:
        st.session_state.show_evaluation = True

    if "interview_questions" not in st.session_state:
        st.warning("⚠️ No interview questions generated yet!")
        if st.button("🤖 Go to Interview Setup", use_container_width=True):
            st.session_state.current_page = "interview_setup"
            st.rerun()
        return

    questions = st.session_state.interview_questions

    if "interview_started" not in st.session_state:
        st.session_state.interview_started = False

    if not st.session_state.interview_started:
        show_interview_start(questions)
        return

    show_interview_session(questions)


def show_interview_start(questions):
    st.subheader("📋 Interview Overview")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Questions", len(questions))
    with col2:
        categories = {q.category.value for q in questions}
        st.metric("Categories", len(categories))
    with col3:
        difficulties = {q.difficulty.value for q in questions}
        st.metric("Difficulties", ", ".join(difficulties))

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        answer_mode = st.radio("Answer Mode", ["Text", "Voice"], horizontal=True)
    with col2:
        show_evaluation = st.checkbox("Show evaluation after each answer", value=True)

    st.session_state.answer_mode = answer_mode.lower()
    st.session_state.show_evaluation = show_evaluation

    if st.button("▶️ Start Interview", type="primary", use_container_width=True):
        create_interview_session(questions)

        st.session_state.current_question_index = 0
        st.session_state.interview_answers = []
        st.session_state.interview_evaluations = []
        st.session_state.question_start_time = time.time()
        st.rerun()


def show_interview_session(questions):
    idx = st.session_state.current_question_index

    if idx >= len(questions):
        show_interview_complete(questions)
        return

    question = questions[idx]

    progress = (idx + 1) / len(questions)
    st.progress(progress, text=f"Question {idx + 1} of {len(questions)}")

    with st.container():
        st.markdown(
            f"""
        <div style='padding: 20px; border-radius: 10px; border: 2px solid #4CAF50; background-color: #f0f8f0;'>
            <h4>🎯 Question {idx + 1} [{question.category.value.title()} - {question.difficulty.value.title()}]</h4>
            <p style='font-size: 1.1em;'>{question.question_text}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.caption("Expected key points: " + ", ".join(question.expected_key_points))

    st.markdown("---")

    answer = ""

    if st.session_state.answer_mode == "text":
        answer = st.text_area(
            "Your Answer",
            height=150,
            placeholder="Type your answer here...",
            key=f"answer_{idx}",
        )
    else:
        st.write("**Voice Answer**")
        audio_file = st.audio_input("Record your answer")

        if audio_file:
            tmp_path = None
            with st.spinner("Transcribing..."):
                try:
                    import tempfile

                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp.write(audio_file.read())
                        tmp_path = tmp.name

                    result = transcribe_audio(tmp_path)
                    answer = result.text
                    st.success(f"Transcribed: {answer}")
                except Exception as e:
                    st.error(f"Transcription failed: {e!s}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "✅ Submit Answer",
            type="primary",
            use_container_width=True,
            disabled=not answer.strip(),
        ):
            with st.spinner("Evaluating your answer..."):
                try:
                    evaluation = evaluate_answer(
                        question=question,
                        answer=answer,
                        resume=st.session_state.resume_analysis,
                        job=st.session_state.job_analysis,
                    )
                except Exception as e:
                    st.error(
                        f"❌ Unable to evaluate your answer at this time. "
                        f"Please try again later or contact support.\n\n"
                        f"Details: {e!s}"
                    )
                    st.stop()
                    return

                st.session_state.interview_answers.append(answer)
                st.session_state.interview_evaluations.append(evaluation)

                save_question_answer(idx, question, answer, evaluation)

                if st.session_state.show_evaluation:
                    show_evaluation_result(evaluation, question)

                st.session_state.current_question_index += 1
                st.rerun()

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if idx > 0 and st.button("← Previous", use_container_width=True):
            st.session_state.current_question_index -= 1
            st.rerun()

    with col3:
        if st.button("Skip →", use_container_width=True):
            st.session_state.interview_answers.append("[SKIPPED]")
            st.session_state.interview_evaluations.append(None)
            st.session_state.current_question_index += 1
            st.rerun()


def show_evaluation_result(evaluation, question):
    st.markdown("---")
    st.subheader("📊 Answer Evaluation")

    cols = st.columns(5)
    metrics = [
        ("Technical", evaluation.technical_accuracy),
        ("Relevance", evaluation.relevance),
        ("Communication", evaluation.communication),
        ("Confidence", evaluation.confidence),
        ("Completeness", evaluation.completeness),
    ]

    for col, (label, score) in zip(cols, metrics):
        with col:
            st.metric(label, f"{score:.1f}/10")

    st.metric("Overall", f"{evaluation.overall_score:.1f}/10")

    tabs = st.tabs(
        [
            "✅ Strengths",
            "⚠️ Weaknesses",
            "📝 Missing",
            "❌ Incorrect",
            "💡 Better Answer",
            "🗣️ Communication",
            "🔧 Technical",
        ]
    )

    with tabs[0]:
        for s in evaluation.strengths:
            st.write(f"• {s}")

    with tabs[1]:
        for w in evaluation.weaknesses:
            st.write(f"• {w}")

    with tabs[2]:
        for m in evaluation.missing_points:
            st.write(f"• {m}")

    with tabs[3]:
        for i in evaluation.incorrect_points:
            st.write(f"• {i}")

    with tabs[4]:
        st.write(evaluation.suggested_answer)

    with tabs[5]:
        st.write(evaluation.communication_feedback)

    with tabs[6]:
        st.write(evaluation.technical_feedback)

    if st.button("Continue →", type="primary"):
        st.rerun()


def show_interview_complete(questions):
    st.balloons()
    st.success("Interview Complete!")

    evaluations = [e for e in st.session_state.interview_evaluations if e is not None]
    skipped = sum(1 for e in st.session_state.interview_evaluations if e is None)

    if skipped:
        st.info(f"{skipped} question(s) were skipped.")

    report = st.session_state.get("interview_report")
    if report is None and evaluations:
        with st.spinner("Generating final report..."):
            try:
                report = generate_interview_report(
                    questions=questions,
                    evaluations=evaluations,
                    resume=st.session_state.resume_analysis,
                    job=st.session_state.job_analysis,
                )
                st.session_state.interview_report = report
            except Exception as e:
                st.error(
                    f"Unable to generate the full interview report. "
                    f"Your {len(evaluations)} answer evaluation(s) are still available below.\n\n"
                    f"Details: {e!s}"
                )
                report = None

    if report is not None:
        try:
            save_interview_completion(report, questions, evaluations)
        except Exception as e:
            st.warning(f"Report generated but failed to save to database: {e!s}")

    st.subheader("Interview Summary")

    if evaluations:
        col1, col2, col3, col4, col5 = st.columns(5)
        avg_scores = {
            "Overall": sum(e.overall_score for e in evaluations) / len(evaluations),
            "Technical": sum(e.technical_accuracy for e in evaluations) / len(evaluations),
            "Communication": sum(e.communication for e in evaluations) / len(evaluations),
            "Relevance": sum(e.relevance for e in evaluations) / len(evaluations),
            "Completeness": sum(e.completeness for e in evaluations) / len(evaluations),
        }

        for col, (label, score) in zip([col1, col2, col3, col4, col5], avg_scores.items()):
            with col:
                st.metric(label, f"{score:.1f}/10")

    if report:
        st.markdown("---")
        st.subheader("Generated Report Summary")
        st.write(f"**Overall Score:** {report.overall_score:.1f}/10")
        if report.strengths:
            st.write("**Strengths:** " + ", ".join(report.strengths[:5]))
        if report.weaknesses:
            st.write("**Weaknesses:** " + ", ".join(report.weaknesses[:5]))

    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("View Full Report", use_container_width=True):
            st.session_state.current_page = "report"
            st.rerun()

    with col2:
        if st.button("Retry Interview", use_container_width=True):
            reset_interview_state()
            st.rerun()

    with col3:
        if st.button("Back to Dashboard", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()


def _ensure_user_session():
    """Create or reuse the UserSession row for the current Streamlit session."""
    if "user_session_id" not in st.session_state:
        import uuid

        st.session_state.user_session_id = str(uuid.uuid4())[:8]

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
        return session.id


def _ensure_resume_job_refs(db, session_id):
    """Resolve resume/job DB ids from session state, falling back to DB rows."""
    resume = None
    job = None
    if "resume_analysis" in st.session_state:
        resume = (
            db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.session_id == session_id)
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )
    if "job_analysis" in st.session_state:
        job = (
            db.query(JobDescription)
            .filter(JobDescription.session_id == session_id)
            .order_by(JobDescription.created_at.desc())
            .first()
        )
    return resume, job


def create_interview_session(questions):
    session_id = _ensure_user_session()

    with get_db_context() as db:
        resume, job = _ensure_resume_job_refs(db, session_id)

        interview = InterviewSession(
            session_id=session_id,
            resume_analysis_id=resume.id if resume else None,
            job_description_id=job.id if job else None,
            interview_type=(
                st.session_state.interview_config.get("type", "Full Interview")
                if "interview_config" in st.session_state
                else "Full Interview"
            ),
            difficulty=(
                st.session_state.interview_config.get("difficulty", "Medium")
                if "interview_config" in st.session_state
                else "Medium"
            ),
            total_questions=len(questions),
            status="in_progress",
            started_at=datetime.now(),
        )

        db.add(interview)
        db.flush()

        for i, q in enumerate(questions):
            db_question = InterviewQuestion(
                interview_session_id=interview.id,
                question_number=i + 1,
                category=q.category.value if hasattr(q.category, "value") else str(q.category),
                difficulty=(
                    q.difficulty.value if hasattr(q.difficulty, "value") else str(q.difficulty)
                ),
                question_text=q.question_text,
                expected_key_points=q.expected_key_points,
            )
            db.add(db_question)

        st.session_state.interview_session_id = interview.id


def save_question_answer(idx, question, answer, evaluation):
    if "interview_session_id" not in st.session_state:
        return
    with get_db_context() as db:
        db_question = (
            db.query(InterviewQuestion)
            .filter(
                InterviewQuestion.interview_session_id == st.session_state.interview_session_id,
                InterviewQuestion.question_number == idx + 1,
            )
            .first()
        )

        if db_question:
            db_question.answer_text = answer
            db_question.answer_mode = st.session_state.answer_mode
            db_question.technical_accuracy = evaluation.technical_accuracy
            db_question.relevance = evaluation.relevance
            db_question.communication = evaluation.communication
            db_question.confidence = evaluation.confidence
            db_question.completeness = evaluation.completeness
            db_question.overall_score = evaluation.overall_score
            db_question.strengths = evaluation.strengths
            db_question.weaknesses = evaluation.weaknesses
            db_question.missing_points = evaluation.missing_points
            db_question.incorrect_points = evaluation.incorrect_points
            db_question.suggested_answer = evaluation.suggested_answer
            db_question.communication_feedback = evaluation.communication_feedback
            db_question.technical_feedback = evaluation.technical_feedback
            db_question.answered_at = datetime.now()
            db_question.evaluated_at = datetime.now()


def save_interview_completion(report, questions, evaluations):
    if "interview_session_id" not in st.session_state:
        return
    with get_db_context() as db:
        interview = (
            db.query(InterviewSession)
            .filter(InterviewSession.id == st.session_state.interview_session_id)
            .first()
        )

        if not interview:
            return

        interview.status = "completed"
        interview.completed_at = datetime.now()
        if report is not None:
            interview.overall_score = report.overall_score
            interview.technical_score = report.technical_score
            interview.communication_score = report.communication_score
            interview.hr_score = report.hr_score
            interview.problem_solving_score = report.problem_solving_score
            interview.strengths = report.strengths
            interview.weaknesses = report.weaknesses
            interview.missed_concepts = report.frequently_missed_concepts
            interview.recommended_topics = report.recommended_topics
            interview.recommended_projects = report.recommended_projects
            interview.recommended_questions = report.recommended_questions
            interview.improvement_plan_7_day = [
                p.model_dump() for p in report.improvement_plan_7_day
            ]
            interview.improvement_plan_30_day = [
                p.model_dump() for p in report.improvement_plan_30_day
            ]


def reset_interview_state():
    keys_to_remove = [
        "interview_started",
        "current_question_index",
        "interview_answers",
        "interview_evaluations",
        "interview_session_id",
        "question_start_time",
    ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
