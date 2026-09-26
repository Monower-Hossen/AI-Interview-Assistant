from pydantic import BaseModel, model_validator

from config.settings import settings
from services.llm_service import get_llm_service

MAX_JD_CHARS = settings.max_jd_chars
_SAFE_JD_CHARS = 3500


def _job_input_limits() -> tuple[int, ...]:
    configured = max(1, int(settings.max_jd_chars))
    safe = min(configured, _SAFE_JD_CHARS)
    return tuple(dict.fromkeys((configured, safe)))


class JobAnalysisResult(BaseModel):
    job_title: str | None = None
    company: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    programming_languages: list[str] = []
    frameworks: list[str] = []
    databases: list[str] = []
    tools: list[str] = []
    experience_requirements: list[str] = []
    education_requirements: list[str] = []
    responsibilities: list[str] = []
    keywords: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def coerce_string_fields(cls, data):
        if not isinstance(data, dict):
            return data
        for field_name in ("experience_requirements", "education_requirements"):
            val = data.get(field_name)
            if val and isinstance(val, str):
                data[field_name] = [val]
            elif val is None:
                data[field_name] = []
        return data


JOB_ANALYSIS_PROMPT = """You are an expert job description analyzer. Analyze the following job description and extract structured information.

JOB DESCRIPTION:
{job_description}

Extract the following information and return as JSON:

1. job_title: The job title/position
2. company: Company name (if mentioned)
3. required_skills: Must-have skills explicitly listed as required
4. preferred_skills: Nice-to-have or preferred skills
5. programming_languages: Programming languages mentioned
6. frameworks: Frameworks and libraries mentioned
7. databases: Database technologies mentioned
8. tools: Development tools, platforms, methodologies mentioned
9. experience_requirements: Years of experience, specific experience requirements
10. education_requirements: Degree requirements, educational qualifications
11. responsibilities: Key responsibilities and duties
12. keywords: Important keywords and phrases for matching

Be precise - only extract information explicitly stated in the job description.

Return ONLY valid JSON matching the schema."""


class JobAnalyzer:
    def __init__(self):
        self.llm = get_llm_service()

    def analyze(self, job_description: str) -> JobAnalysisResult:
        job_description = job_description[:MAX_JD_CHARS]

        prompt = JOB_ANALYSIS_PROMPT.format(job_description=job_description)
        result = self.llm.generate_structured(prompt, JobAnalysisResult)
        return result


def analyze_job_description(job_description: str) -> JobAnalysisResult:
    analyzer = JobAnalyzer()
    return analyzer.analyze(job_description)
