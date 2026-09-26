import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from services.answer_evaluator import AnswerEvaluation
from services.interview_generator import InterviewQuestion
from services.job_analyzer import JobAnalysisResult
from services.llm_service import get_llm_service
from services.resume_analyzer import ResumeAnalysisResult


class ImprovementPlanItem(BaseModel):
    day: int
    focus: str
    activity: str
    resources: list[str] = Field(default_factory=list)
    estimated_hours: float

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_plan(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        data = dict(value)
        if "estimated_hours" not in data and "hours" in data:
            data["estimated_hours"] = data["hours"]
        if "day" not in data and "week" in data:
            data["day"] = data["week"]
        if "focus" not in data and "milestone" in data:
            data["focus"] = data["milestone"]
        if "activity" not in data and "milestone" in data:
            data["activity"] = data["milestone"]
        return data

    @field_validator("resources", mode="before")
    @classmethod
    def normalize_resources(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [resource.strip() for resource in re.split(r"[,\n]+", value) if resource.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(resource).strip() for resource in value if str(resource).strip()]
        return value


class InterviewReport(BaseModel):
    overall_score: float = Field(ge=0, le=10)
    technical_score: float = Field(ge=0, le=10)
    communication_score: float = Field(ge=0, le=10)
    hr_score: float = Field(ge=0, le=10)
    problem_solving_score: float = Field(ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    frequently_missed_concepts: list[str] = Field(default_factory=list)
    recommended_topics: list[str] = Field(default_factory=list)
    recommended_projects: list[str] = Field(default_factory=list)
    recommended_questions: list[str] = Field(default_factory=list)
    improvement_plan_7_day: list[ImprovementPlanItem] = Field(default_factory=list)
    improvement_plan_30_day: list[ImprovementPlanItem] = Field(default_factory=list)


REPORT_GENERATION_PROMPT = """You are an expert career coach. Generate a comprehensive interview performance report.

INTERVIEW SUMMARY:
- Total Questions: {total_questions}
- Categories Covered: {categories}
- Average Scores: Technical={avg_technical:.1f}, Communication={avg_comm:.1f}, Relevance={avg_relevance:.1f}, Completeness={avg_complete:.1f}

QUESTION-BY-QUESTION BREAKDOWN:
{question_breakdown}

CANDIDATE PROFILE:
{resume_summary}

TARGET JOB:
{job_summary}

Generate a detailed report with:

1. overall_score: Weighted overall (0-10)
2. technical_score: Average technical accuracy for technical questions (0-10)
3. communication_score: Average communication score (0-10)
4. hr_score: Average score for HR/behavioral/situational questions (0-10)
5. problem_solving_score: Inferred from technical + situational answers (0-10)
6. strengths: Top 5-7 strengths demonstrated
7. weaknesses: Top 5-7 areas for improvement
8. frequently_missed_concepts: Concepts missed across multiple questions
9. recommended_topics: Topics to study (specific, actionable)
10. recommended_projects: Project ideas to build portfolio
11. recommended_questions: Questions to practice for next interview
12. improvement_plan_7_day: exactly 7 objects. Each object must use this exact shape:
    {"day": 1, "focus": "topic", "activity": "action", "resources": ["resource 1", "resource 2"], "estimated_hours": 2.0}
13. improvement_plan_30_day: exactly 4 objects using the same exact shape. For this plan, set day to the week number (1-4), focus to the milestone, activity to the planned activity, resources to a list, and estimated_hours to a number.
Do not use "hours", "week", or "milestone" as field names; use "estimated_hours", "day", "focus", and "activity" exactly.

Be specific and actionable. Reference actual interview content.

Return ONLY valid JSON matching the schema."""


class ReportGenerator:
    def __init__(self):
        self.llm = get_llm_service()

    def generate(
        self,
        questions: list[InterviewQuestion],
        evaluations: list[AnswerEvaluation],
        resume: ResumeAnalysisResult,
        job: JobAnalysisResult,
    ) -> InterviewReport:

        tech_scores = [e.technical_accuracy for e in evaluations]
        comm_scores = [e.communication for e in evaluations]
        relevance_scores = [e.relevance for e in evaluations]
        complete_scores = [e.completeness for e in evaluations]

        breakdown_lines = []
        for i, (q, e) in enumerate(zip(questions, evaluations)):
            breakdown_lines.append(
                f"Q{i+1} [{q.category.value}/{q.difficulty.value}]: "
                f"Tech={e.technical_accuracy:.1f}, Comm={e.communication:.1f}, "
                f"Rel={e.relevance:.1f}, Comp={e.completeness:.1f}, "
                f"Overall={e.overall_score:.1f} - {q.question_text[:80]}..."
            )
        question_breakdown = "\n".join(breakdown_lines)

        resume_summary = f"""
Name: {resume.candidate_name or 'N/A'}
Experience: {len(resume.experience)} roles
Skills: {', '.join(resume.skills[:15])}
Projects: {len(resume.projects)}
"""

        job_summary = f"""
Title: {job.job_title or 'N/A'}
Required: {', '.join(job.required_skills[:10])}
Responsibilities: {', '.join(job.responsibilities[:5])}
"""

        prompt = REPORT_GENERATION_PROMPT.format(
            total_questions=len(questions),
            categories=", ".join({q.category.value for q in questions}),
            avg_technical=sum(tech_scores) / len(tech_scores) if tech_scores else 0,
            avg_comm=sum(comm_scores) / len(comm_scores) if comm_scores else 0,
            avg_relevance=(
                sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            ),
            avg_complete=(sum(complete_scores) / len(complete_scores) if complete_scores else 0),
            question_breakdown=question_breakdown,
            resume_summary=resume_summary,
            job_summary=job_summary,
        )

        result = self.llm.generate_structured(prompt, InterviewReport)
        return result


def generate_interview_report(
    questions: list[InterviewQuestion],
    evaluations: list[AnswerEvaluation],
    resume: ResumeAnalysisResult,
    job: JobAnalysisResult,
) -> InterviewReport:
    generator = ReportGenerator()
    return generator.generate(questions, evaluations, resume, job)
