from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from services.job_analyzer import MAX_JD_CHARS, JobAnalysisResult
from services.job_matcher import ResumeJobMatchResult
from services.llm_service import get_llm_service
from services.resume_analyzer import MAX_RESUME_CHARS, ResumeAnalysisResult
from utils.helpers import truncate_text


class QuestionCategory(str, Enum):
    TECHNICAL = "technical"
    HR = "hr"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    PROJECT_BASED = "project_based"
    RESUME_BASED = "resume_based"
    JOB_SPECIFIC = "job_specific"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InterviewQuestion(BaseModel):
    question_number: int
    category: QuestionCategory
    difficulty: Difficulty
    question_text: str
    expected_key_points: list[str] = []
    follow_up_hints: list[str] = []


_VALID_CATEGORIES = {c.value for c in QuestionCategory}
_VALID_DIFFICULTIES = {d.value for d in Difficulty}


def _normalize_label(value: Any, default: str) -> str:
    if value is None:
        return default

    label = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if not label:
        return default
    return label


class QuestionSet(BaseModel):
    questions: list[InterviewQuestion]
    total_count: int = 0
    category_distribution: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def coerce_missing_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        data = dict(data)
        questions = data.get("questions")
        if isinstance(questions, list):
            fixed_questions = []
            for i, q in enumerate(questions):
                if isinstance(q, str):
                    fixed_questions.append({
                        "question_number": i + 1,
                        "category": "technical",
                        "difficulty": "medium",
                        "question_text": q,
                        "expected_key_points": [],
                        "follow_up_hints": [],
                    })
                    continue

                if not isinstance(q, dict):
                    if hasattr(q, "model_dump"):
                        q = q.model_dump()
                    else:
                        continue

                item = dict(q)
                item["question_number"] = item.get("question_number") or i + 1

                category = _normalize_label(item.get("category"), "technical")
                item["category"] = category if category in _VALID_CATEGORIES else "technical"

                difficulty = _normalize_label(item.get("difficulty"), "medium")
                item["difficulty"] = difficulty if difficulty in _VALID_DIFFICULTIES else "medium"

                item["question_text"] = item.get("question_text") or item.get("question") or ""
                for key in ("expected_key_points", "follow_up_hints"):
                    value = item.get(key)
                    if value is None:
                        item[key] = []
                    elif isinstance(value, str):
                        item[key] = [value]
                    elif isinstance(value, list):
                        item[key] = [str(v) for v in value]
                    else:
                        item[key] = []
                fixed_questions.append(item)

            data["questions"] = fixed_questions
            data["total_count"] = len(fixed_questions)

        distribution = data.get("category_distribution")
        if isinstance(distribution, dict) and distribution:
            data["category_distribution"] = {
                _normalize_label(k, "technical"): v for k, v in distribution.items()
            }
        elif isinstance(data.get("questions"), list):
            derived: dict[str, int] = {}
            for q in data["questions"]:
                key = q.get("category", "technical") if isinstance(q, dict) else "technical"
                derived[key] = derived.get(key, 0) + 1
            data["category_distribution"] = derived

        return data


QUESTION_GENERATION_PROMPT = """You are an expert interview coach. Generate personalized interview questions based on the candidate's resume, target job, and skill gaps.

CANDIDATE RESUME:
{resume_json}

TARGET JOB:
{job_json}

MATCH ANALYSIS:
{match_json}

CONFIGURATION:
- Total questions needed: {total_questions}
- Difficulty: {difficulty}
- Categories to include: {categories}
- Focus areas: {focus_areas}

Generate {total_questions} highly personalized interview questions. Distribute across categories:
- Technical: Core technical skills from job requirements
- HR: Cultural fit, motivation, career goals
- Behavioral: Past behavior predicting future performance (STAR method)
- Situational: Hypothetical scenarios relevant to the role
- Project-based: Deep dive into candidate's projects
- Resume-based: Clarification and deep-dive on resume claims
- Job-specific: Questions tailored to this specific role

Each question must have:
1. question_number: Sequential number (1 to {total_questions})
2. category: One of the 7 categories above (lowercase: technical, hr, behavioral, situational, project_based, resume_based, job_specific)
3. difficulty: easy, medium, or hard
4. question_text: The actual question (personalized, not generic)
5. expected_key_points: 3-5 key points a strong answer should cover
6. follow_up_hints: 2-3 hints for follow-up questions based on answer

Avoid generic questions like "Tell me about yourself" unless specifically needed.
Make questions specific to the candidate's background and the target role.

Return ONLY valid JSON matching this exact structure:
{{
  "questions": [
    {{
      "question_number": 1,
      "category": "technical",
      "difficulty": "medium",
      "question_text": "Your personalized question here",
      "expected_key_points": ["point 1", "point 2", "point 3"],
      "follow_up_hints": ["hint 1", "hint 2"]
    }}
  ],
  "total_count": {total_questions},
  "category_distribution": {{"technical": 3, "hr": 2, "behavioral": 2, "situational": 1, "project_based": 1, "resume_based": 1, "job_specific": 1}}
}}

The category_distribution must sum to total_count ({total_questions}). Use lowercase category names."""


RETRY_QUESTION_PROMPT = """Generate {total_questions} interview questions. Return ONLY a single valid JSON object with this EXACT structure:

{
  "questions": [
    {"question_number": 1, "category": "technical", "difficulty": "medium", "question_text": "Your question here", "expected_key_points": ["point 1", "point 2"], "follow_up_hints": ["hint 1"]},
    {"question_number": 2, "category": "hr", "difficulty": "medium", "question_text": "Your question here", "expected_key_points": ["point 1", "point 2"], "follow_up_hints": ["hint 1"]}
  ],
  "total_count": {total_questions},
  "category_distribution": {"technical": 1, "hr": 1}
}

CRITICAL RULES:
- "questions" MUST be an array of OBJECTS (not strings)
- Each question object MUST have: question_number (int), category (lowercase), difficulty (easy/medium/hard), question_text (string), expected_key_points (array of strings), follow_up_hints (array of strings)
- "category_distribution" MUST use lowercase keys and sum to total_count
- NO markdown, NO explanation, NO ```json fences
- Return ONLY the JSON object"""


class InterviewGenerator:
    def __init__(self):
        self.llm = get_llm_service()

    def generate(
        self,
        resume: ResumeAnalysisResult,
        job: JobAnalysisResult,
        match: ResumeJobMatchResult,
        total_questions: int = 5,
        difficulty: str = "medium",
        categories: list[QuestionCategory] | None = None,
        focus_areas: list[str] | None = None,
    ) -> QuestionSet:

        if categories is None:
            categories = [
                QuestionCategory.TECHNICAL,
                QuestionCategory.HR,
                QuestionCategory.BEHAVIORAL,
                QuestionCategory.SITUATIONAL,
                QuestionCategory.PROJECT_BASED,
                QuestionCategory.RESUME_BASED,
                QuestionCategory.JOB_SPECIFIC,
            ]

        category_names = [c.value for c in categories]
        focus = focus_areas or []

        for missing in match.missing_skills:
            if missing.importance in ["critical", "important"]:
                focus.append(f"Missing skill: {missing.skill}")

        prompt = QUESTION_GENERATION_PROMPT.format(
            resume_json=truncate_text(resume.model_dump_json(indent=2), MAX_RESUME_CHARS),
            job_json=truncate_text(job.model_dump_json(indent=2), MAX_JD_CHARS),
            match_json=truncate_text(match.model_dump_json(indent=2), MAX_JD_CHARS),
            total_questions=total_questions,
            difficulty=difficulty,
            categories=", ".join(category_names),
            focus_areas=", ".join(focus) if focus else "None specified",
        )

        try:
            result = self.llm.generate_structured(prompt, QuestionSet)
            return result
        except Exception:
            retry_prompt = RETRY_QUESTION_PROMPT.replace("{total_questions}", str(total_questions))
            retry_prompt = retry_prompt + f"\n\nRESUME:\n{truncate_text(resume.model_dump_json(indent=2), MAX_RESUME_CHARS)}\n\nJOB:\n{truncate_text(job.model_dump_json(indent=2), MAX_JD_CHARS)}\n\nMATCH:\n{truncate_text(match.model_dump_json(indent=2), MAX_JD_CHARS)}"

            try:
                return self.llm.generate_structured(retry_prompt, QuestionSet, max_tokens=3000)
            except Exception:
                pass

        # Fallback
        return QuestionSet(
            questions=[],
            total_count=total_questions,
            category_distribution={}
        )

    def generate_follow_up(
        self,
        previous_question: InterviewQuestion,
        candidate_answer: str,
        resume: ResumeAnalysisResult,
        job: JobAnalysisResult,
    ) -> InterviewQuestion:

        FOLLOW_UP_PROMPT = """Generate a relevant follow-up question based on the candidate's answer.

PREVIOUS QUESTION:
Category: {category}
Difficulty: {difficulty}
Question: {question}
Expected key points: {key_points}

CANDIDATE'S ANSWER:
{answer}

CANDIDATE CONTEXT:
{resume_summary}

Generate ONE follow-up question that:
1. Probes deeper based on their answer
2. Addresses gaps or vague points in their response
3. Is personalized to their background
4. Maintains appropriate difficulty

Return as JSON matching InterviewQuestion schema."""

        resume_summary = f"""
Name: {resume.candidate_name}
Experience: {len(resume.experience)} roles
Key Skills: {', '.join(resume.skills[:10])}
Projects: {len(resume.projects)}
"""

        prompt = FOLLOW_UP_PROMPT.format(
            category=previous_question.category.value,
            difficulty=previous_question.difficulty.value,
            question=previous_question.question_text,
            key_points=", ".join(previous_question.expected_key_points),
            answer=candidate_answer,
            resume_summary=resume_summary,
        )

        result = self.llm.generate_structured(prompt, InterviewQuestion)
        return result


def generate_interview_questions(
    resume: ResumeAnalysisResult,
    job: JobAnalysisResult,
    match: ResumeJobMatchResult,
    total_questions: int = 10,
    difficulty: str = "medium",
    categories: list[QuestionCategory] | None = None,
) -> QuestionSet:
    generator = InterviewGenerator()
    return generator.generate(resume, job, match, total_questions, difficulty, categories)
