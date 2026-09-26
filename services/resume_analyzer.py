import logging

from pydantic import BaseModel, Field, model_validator

from config.settings import settings
from services.llm_service import get_llm_service, is_payload_too_large_error
from utils.helpers import (
    compact_text,
    deduplicate_skills,
    extract_email,
    extract_github,
    extract_linkedin,
    extract_phone,
    extract_portfolio,
)

logger = logging.getLogger(__name__)


class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str | None = None
    grade: str | None = None
    details: str | None = None


class ExperienceItem(BaseModel):
    title: str = ""
    company: str = ""
    duration: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    role: str | None = None
    duration: str | None = None


class ResumeAnalysisResult(BaseModel):
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_item_lists(cls, data):
        if not isinstance(data, dict):
            return data
        for field_name, default_key in (
            ("education", "degree"),
            ("experience", "title"),
            ("projects", "name"),
        ):
            val = data.get(field_name)
            if isinstance(val, dict):
                data[field_name] = [val]
            elif val and isinstance(val, list) and isinstance(val[0], str):
                data[field_name] = [{default_key: v} for v in val]
        return data


class ResumeScores(BaseModel):
    technical_skills: float = Field(default=0, ge=0, le=100)
    experience: float = Field(default=0, ge=0, le=100)
    projects: float = Field(default=0, ge=0, le=100)
    education: float = Field(default=0, ge=0, le=100)
    certifications: float = Field(default=0, ge=0, le=100)
    structure: float = Field(default=0, ge=0, le=100)
    overall: float = Field(default=0, ge=0, le=100)


class ResumeAnalysisWithScores(BaseModel):
    analysis: ResumeAnalysisResult = Field(default_factory=ResumeAnalysisResult)
    scores: ResumeScores | None = None

    @model_validator(mode="before")
    @classmethod
    def coerce_flat_analysis(cls, data):
        if not isinstance(data, dict):
            return {"analysis": {}}

        data = dict(data)
        analysis_fields = {
            "candidate_name",
            "email",
            "phone",
            "linkedin",
            "github",
            "portfolio",
            "education",
            "experience",
            "skills",
            "programming_languages",
            "frameworks",
            "databases",
            "tools",
            "projects",
            "certifications",
            "strengths",
            "weaknesses",
        }
        score_fields = {
            "technical_skills",
            "experience",
            "projects",
            "education",
            "certifications",
            "structure",
            "overall",
        }

        if "analysis" not in data:
            if any(key in data for key in analysis_fields):
                analysis = {key: data[key] for key in analysis_fields if key in data}
                scores = data.get("scores")
                return {"analysis": analysis, "scores": scores}

            item_fields = {
                "education": {"degree", "institution", "year", "grade", "details"},
                "experience": {"title", "company", "duration", "description", "technologies"},
                "projects": {"name", "description", "technologies", "role", "duration"},
            }
            analysis = {}
            for field_name, keys in item_fields.items():
                if any(key in data for key in keys):
                    analysis[field_name] = [{key: data[key] for key in keys if key in data}]
            scores = {key: data[key] for key in score_fields if key in data}
            return {"analysis": analysis, "scores": scores or None}

        if isinstance(data["analysis"], list) and len(data["analysis"]) == 1:
            if isinstance(data["analysis"][0], dict):
                data["analysis"] = data["analysis"][0]
        return data


MAX_RESUME_CHARS = settings.max_resume_chars
_SAFE_RESUME_CHARS = 3500
_RESUME_ANALYSIS_MAX_TOKENS = 1800


def _resume_input_limits() -> tuple[int, ...]:
    configured = max(1, int(settings.max_resume_chars))
    safe = min(configured, _SAFE_RESUME_CHARS)
    return tuple(dict.fromkeys((configured, safe)))


RESUME_ANALYSIS_AND_SCORING_PROMPT = """You are a fast, accurate resume parser and evaluator.

Analyze the resume below in ONE pass.

Return this EXACT JSON shape (no extra keys, no markdown, no explanation):
{
  "analysis": {
    "candidate_name": null,
    "email": null,
    "phone": null,
    "linkedin": null,
    "github": null,
    "portfolio": null,
    "education": [],
    "experience": [],
    "skills": [],
    "programming_languages": [],
    "frameworks": [],
    "databases": [],
    "tools": [],
    "projects": [],
    "certifications": [],
    "strengths": [],
    "weaknesses": []
  },
  "scores": {
    "technical_skills": 0,
    "experience": 0,
    "projects": 0,
    "education": 0,
    "certifications": 0,
    "structure": 0,
    "overall": 0
  }
}

Rules:
- Extract only information supported by the resume.
- Do not invent employers, skills, dates, projects, or certifications.
- Keep descriptions concise.
- Keep strengths/weaknesses concise.
- Score based only on evidence in the resume.
- Return numbers from 0 to 100.
- Output JSON only. No leading/trailing whitespace. No newlines before first brace.

RESUME:
{resume_text}
"""


def _clean_analysis(result: ResumeAnalysisResult, resume_text: str) -> ResumeAnalysisResult:
    result.email = result.email or extract_email(resume_text)
    result.phone = result.phone or extract_phone(resume_text)
    result.linkedin = result.linkedin or extract_linkedin(resume_text)
    result.github = result.github or extract_github(resume_text)
    result.portfolio = result.portfolio or extract_portfolio(resume_text)

    result.skills = deduplicate_skills(result.skills)
    result.programming_languages = deduplicate_skills(result.programming_languages)
    result.frameworks = deduplicate_skills(result.frameworks)
    result.databases = deduplicate_skills(result.databases)
    result.tools = deduplicate_skills(result.tools)
    result.certifications = deduplicate_skills(result.certifications)
    return result


def _create_empty_analysis() -> tuple[ResumeAnalysisResult, ResumeScores]:
    empty_analysis = ResumeAnalysisResult()
    empty_scores = ResumeScores(
        technical_skills=0,
        experience=0,
        projects=0,
        education=0,
        certifications=0,
        structure=0,
        overall=0,
    )
    return empty_analysis, empty_scores


class ResumeAnalyzer:
    def __init__(self):
        self.llm = get_llm_service()

    def analyze_and_score(self, resume_text: str):
        if not resume_text or not resume_text.strip():
            raise ValueError("Resume text is empty.")

        last_exc = None
        for max_chars in _resume_input_limits():
            clean_text = compact_text(resume_text, max_chars)
            prompt = RESUME_ANALYSIS_AND_SCORING_PROMPT.replace("{resume_text}", clean_text)
            max_tokens = 2200 if len(clean_text) <= 2500 else 2800

            try:
                result: ResumeAnalysisWithScores = self.llm.generate_structured(
                    prompt,
                    ResumeAnalysisWithScores,
                    max_tokens=max_tokens,
                    temperature=0.1,
                    json_mode=True,
                )

                analysis = _clean_analysis(result.analysis, resume_text)
                scores = result.scores or ResumeScores()
                return analysis, scores
            except Exception as exc:
                last_exc = exc
                if not is_payload_too_large_error(exc):
                    break

        logger.warning(f"Resume analysis failed, using fallback: {last_exc}")
        return _create_empty_analysis()

    def analyze(self, resume_text: str) -> ResumeAnalysisResult:
        analysis, _ = self.analyze_and_score(resume_text)
        return analysis

    def score_resume(self, analysis: ResumeAnalysisResult) -> ResumeScores:
        raise RuntimeError(
            "score_resume() is intentionally disabled for fast mode. "
            "Use analyze_and_score() so analysis and scoring happen in one API call."
        )


def analyze_resume(resume_text: str):
    return ResumeAnalyzer().analyze_and_score(resume_text)
