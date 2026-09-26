from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_active = Column(DateTime, default=func.now())

    resume_analyses = relationship(
        "ResumeAnalysis", back_populates="session", cascade="all, delete-orphan"
    )
    job_descriptions = relationship(
        "JobDescription", back_populates="session", cascade="all, delete-orphan"
    )
    interview_sessions = relationship(
        "InterviewSession", back_populates="session", cascade="all, delete-orphan"
    )


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_hash = Column(String(64))

    raw_text = Column(Text)
    candidate_name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))
    linkedin = Column(String(200))
    github = Column(String(200))
    portfolio = Column(String(200))

    education = Column(JSON)
    experience = Column(JSON)
    skills = Column(JSON)
    programming_languages = Column(JSON)
    frameworks = Column(JSON)
    databases = Column(JSON)
    tools = Column(JSON)
    projects = Column(JSON)
    certifications = Column(JSON)
    strengths = Column(JSON)
    weaknesses = Column(JSON)

    technical_skills_score = Column(Float)
    experience_score = Column(Float)
    projects_score = Column(Float)
    education_score = Column(Float)
    certifications_score = Column(Float)
    structure_score = Column(Float)
    overall_resume_score = Column(Float)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    session = relationship("UserSession", back_populates="resume_analyses")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False, index=True)
    title = Column(String(200))
    company = Column(String(200))
    raw_text = Column(Text)
    source = Column(String(50))

    required_skills = Column(JSON)
    preferred_skills = Column(JSON)
    programming_languages = Column(JSON)
    frameworks = Column(JSON)
    databases = Column(JSON)
    tools = Column(JSON)
    experience_requirements = Column(JSON)
    education_requirements = Column(JSON)
    responsibilities = Column(JSON)
    keywords = Column(JSON)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    session = relationship("UserSession", back_populates="job_descriptions")
    match_analyses = relationship(
        "ResumeJobMatch", back_populates="job_description", cascade="all, delete-orphan"
    )


class ResumeJobMatch(Base):
    __tablename__ = "resume_job_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_analysis_id = Column(
        Integer, ForeignKey("resume_analyses.id"), nullable=False, index=True
    )
    job_description_id = Column(
        Integer, ForeignKey("job_descriptions.id"), nullable=False, index=True
    )

    technical_skills_match = Column(Float)
    experience_match = Column(Float)
    projects_match = Column(Float)
    education_match = Column(Float)
    overall_match = Column(Float)

    matching_skills = Column(JSON)
    missing_skills = Column(JSON)
    skill_gaps = Column(JSON)
    experience_gaps = Column(JSON)
    recommendations = Column(JSON)

    created_at = Column(DateTime, default=func.now())

    resume_analysis = relationship("ResumeAnalysis")
    job_description = relationship("JobDescription", back_populates="match_analyses")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False, index=True)
    resume_analysis_id = Column(Integer, ForeignKey("resume_analyses.id"), nullable=True)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=True)

    interview_type = Column(String(50))
    difficulty = Column(String(20))
    total_questions = Column(Integer, default=0)
    current_question_index = Column(Integer, default=0)

    status = Column(String(30), default="created")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    overall_score = Column(Float)
    technical_score = Column(Float)
    communication_score = Column(Float)
    hr_score = Column(Float)
    problem_solving_score = Column(Float)

    strengths = Column(JSON)
    weaknesses = Column(JSON)
    missed_concepts = Column(JSON)
    recommended_topics = Column(JSON)
    recommended_projects = Column(JSON)
    recommended_questions = Column(JSON)
    improvement_plan_7_day = Column(JSON)
    improvement_plan_30_day = Column(JSON)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    session = relationship("UserSession", back_populates="interview_sessions")
    resume_analysis = relationship("ResumeAnalysis")
    job_description = relationship("JobDescription")
    questions = relationship(
        "InterviewQuestion",
        back_populates="interview_session",
        cascade="all, delete-orphan",
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    interview_session_id = Column(
        Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True
    )

    question_number = Column(Integer, nullable=False)
    category = Column(String(50))
    difficulty = Column(String(20))
    question_text = Column(Text, nullable=False)
    expected_key_points = Column(JSON)

    answer_text = Column(Text)
    answer_audio_path = Column(String(500))
    answer_mode = Column(String(20))

    technical_accuracy = Column(Float)
    relevance = Column(Float)
    communication = Column(Float)
    confidence = Column(Float)
    completeness = Column(Float)
    overall_score = Column(Float)

    strengths = Column(JSON)
    weaknesses = Column(JSON)
    missing_points = Column(JSON)
    incorrect_points = Column(JSON)
    suggested_answer = Column(Text)
    communication_feedback = Column(Text)
    technical_feedback = Column(Text)

    asked_at = Column(DateTime, default=func.now())
    answered_at = Column(DateTime, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)

    interview_session = relationship("InterviewSession", back_populates="questions")


class InterviewProgress(Base):
    __tablename__ = "interview_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False, index=True)

    total_interviews = Column(Integer, default=0)
    total_questions_answered = Column(Integer, default=0)
    average_overall_score = Column(Float)
    average_technical_score = Column(Float)
    average_communication_score = Column(Float)
    average_hr_score = Column(Float)

    skill_scores = Column(JSON)
    skill_gaps = Column(JSON)
    strong_areas = Column(JSON)
    weak_areas = Column(JSON)

    score_history = Column(JSON)

    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    session = relationship("UserSession")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False, index=True)
    source_type = Column(String(30))
    source_id = Column(Integer, nullable=True)

    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    embedding = Column(JSON)

    created_at = Column(DateTime, default=func.now())
