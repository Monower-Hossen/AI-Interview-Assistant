import json

from pydantic import BaseModel, Field

from services.job_analyzer import JobAnalysisResult
from services.llm_service import get_llm_service
from services.resume_analyzer import ResumeAnalysisResult


class SkillMatch(BaseModel):
    skill: str
    resume_evidence: str
    job_requirement: str
    match_strength: str


class MissingSkill(BaseModel):
    skill: str
    job_requirement: str
    importance: str
    learning_resources: list[str] = []


class ExperienceGap(BaseModel):
    area: str
    job_requirement: str
    resume_status: str
    gap_description: str


class ResumeJobMatchResult(BaseModel):
    technical_skills_match: float = Field(ge=0, le=100)
    experience_match: float = Field(ge=0, le=100)
    projects_match: float = Field(ge=0, le=100)
    education_match: float = Field(ge=0, le=100)
    overall_match: float = Field(ge=0, le=100)
    matching_skills: list[SkillMatch] = []
    missing_skills: list[MissingSkill] = []
    skill_gaps: list[str] = []
    experience_gaps: list[ExperienceGap] = []
    recommendations: list[str] = []


MATCHING_PROMPT = """You are an expert career coach and hiring manager. Compare the resume analysis with the job description analysis and provide a detailed match assessment.

RESUME ANALYSIS:
{resume_json}

JOB DESCRIPTION ANALYSIS:
{job_json}

Provide a comprehensive match analysis as JSON with:

1. technical_skills_match: Percentage (0-100) - How well technical skills align
2. experience_match: Percentage (0-100) - Experience relevance and depth
3. projects_match: Percentage (0-100) - Project relevance to the role
4. education_match: Percentage (0-100) - Education requirements satisfaction
5. overall_match: Weighted overall percentage (0-100)
6. matching_skills: Array of objects with skill, resume_evidence, job_requirement, match_strength
7. missing_skills: Array of objects with skill, job_requirement, importance, learning_resources
8. skill_gaps: List of strings describing specific skill gaps
9. experience_gaps: Array of objects with area, job_requirement, resume_status, gap_description
10. recommendations: List of actionable recommendation strings

CRITICAL: Return a single JSON OBJECT (not an array) with ALL 10 fields listed above. The top level must be an object, not an array. Do not omit any required fields.

Be honest and specific. Use evidence from both documents.

Return ONLY valid JSON matching the schema."""


RETRY_MATCHING_PROMPT = """You are an expert career coach. Compare a resume against a job description and output ONLY a single JSON object with these exact fields:

{
  "technical_skills_match": 0-100,
  "experience_match": 0-100,
  "projects_match": 0-100,
  "education_match": 0-100,
  "overall_match": 0-100,
  "matching_skills": [{"skill": "...", "resume_evidence": "...", "job_requirement": "...", "match_strength": "strong/moderate/weak"}],
  "missing_skills": [{"skill": "...", "job_requirement": "...", "importance": "critical/important/nice_to_have", "learning_resources": []}],
  "skill_gaps": ["...", "..."],
  "experience_gaps": [{"area": "...", "job_requirement": "...", "resume_status": "...", "gap_description": "..."}],
  "recommendations": ["...", "..."]
}

Resume data: {resume_json}
Job data: {job_json}

Return ONLY the JSON object. No markdown, no explanation."""


MAX_RESUME_CHARS = 6000
MAX_JD_CHARS = 4000


class ResumeJobMatcher:
    def __init__(self):
        self.llm = get_llm_service()

    def match(self, resume: ResumeAnalysisResult, job: JobAnalysisResult) -> ResumeJobMatchResult:
        resume_json = resume.model_dump_json(indent=2)[:MAX_RESUME_CHARS]
        job_json = job.model_dump_json(indent=2)[:MAX_JD_CHARS]

        prompt = MATCHING_PROMPT.format(resume_json=resume_json, job_json=job_json)

        try:
            result = self.llm.generate_structured(prompt, ResumeJobMatchResult)
            return result
        except Exception:
            retry_prompt = RETRY_MATCHING_PROMPT.replace("{resume_json}", resume_json).replace(
                "{job_json}", job_json
            )
            try:
                retry_response = self.llm.generate(retry_prompt, max_tokens=3000)
                parsed = json.loads(retry_response.content)
                if isinstance(parsed, dict):
                    return ResumeJobMatchResult(**parsed)
            except Exception:
                pass

        return ResumeJobMatchResult(
            technical_skills_match=0,
            experience_match=0,
            projects_match=0,
            education_match=0,
            overall_match=0,
            matching_skills=[],
            missing_skills=[],
            skill_gaps=[],
            experience_gaps=[],
            recommendations=["Match analysis could not be completed. Please try again."],
        )


def match_resume_job(resume: ResumeAnalysisResult, job: JobAnalysisResult) -> ResumeJobMatchResult:
    matcher = ResumeJobMatcher()
    return matcher.match(resume, job)
