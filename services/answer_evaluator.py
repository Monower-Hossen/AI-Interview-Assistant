from pydantic import BaseModel, Field

from services.interview_generator import InterviewQuestion
from services.job_analyzer import JobAnalysisResult
from services.llm_service import get_llm_service
from services.resume_analyzer import ResumeAnalysisResult


class AnswerEvaluation(BaseModel):
    technical_accuracy: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10)
    communication: float = Field(ge=0, le=10)
    confidence: float = Field(ge=0, le=10)
    completeness: float = Field(ge=0, le=10)
    overall_score: float = Field(ge=0, le=10)
    strengths: list[str] = []
    weaknesses: list[str] = []
    missing_points: list[str] = []
    incorrect_points: list[str] = []
    suggested_answer: str
    communication_feedback: str
    technical_feedback: str


ANSWER_EVALUATION_PROMPT = """You are an expert interview evaluator. Evaluate the candidate's answer to the interview question.

QUESTION:
Category: {category}
Difficulty: {difficulty}
Question: {question}
Expected Key Points: {key_points}

CANDIDATE'S ANSWER:
{answer}

CANDIDATE CONTEXT:
{resume_context}

JOB CONTEXT:
{job_context}

Evaluate the answer across these dimensions (0-10 each):

1. technical_accuracy: Correctness of technical content (N/A for non-technical questions - use 5 as neutral)
2. relevance: How well the answer addresses the question
3. communication: Clarity, structure, and articulation
4. confidence: Inferred confidence from answer quality (text only - be conservative)
5. completeness: Coverage of expected key points
6. overall_score: Weighted overall score

Also provide:
- strengths: What was good in the answer
- weaknesses: What could be improved
- missing_points: Expected points not covered
- incorrect_points: Any factual errors or misconceptions
- suggested_answer: A stronger example answer
- communication_feedback: Specific feedback on communication style
- technical_feedback: Specific feedback on technical content

IMPORTANT:
- For non-technical categories (HR, behavioral, situational), set technical_accuracy to 5 (neutral)
- For confidence, only infer from text quality - do not overclaim
- Be honest and constructive
- If answer is empty/very short, score accordingly

Return ONLY valid JSON matching the schema."""


class AnswerEvaluator:
    def __init__(self):
        self.llm = get_llm_service()

    def evaluate(
        self,
        question: InterviewQuestion,
        answer: str,
        resume: ResumeAnalysisResult,
        job: JobAnalysisResult,
    ) -> AnswerEvaluation:

        resume_context = f"""
Candidate: {resume.candidate_name or 'Not specified'}
Experience: {len(resume.experience)} roles
Key Skills: {', '.join(resume.skills[:15])}
Projects: {len(resume.projects)}
"""

        job_context = f"""
Target Role: {job.job_title or 'Not specified'}
Required Skills: {', '.join(job.required_skills[:10])}
Key Responsibilities: {', '.join(job.responsibilities[:5])}
"""

        prompt = ANSWER_EVALUATION_PROMPT.format(
            category=question.category.value,
            difficulty=question.difficulty.value,
            question=question.question_text,
            key_points=", ".join(question.expected_key_points),
            answer=answer if answer.strip() else "[No answer provided]",
            resume_context=resume_context,
            job_context=job_context,
        )

        result = self.llm.generate_structured(prompt, AnswerEvaluation)
        return result

    def evaluate_batch(
        self,
        questions: list[InterviewQuestion],
        answers: list[str],
        resume: ResumeAnalysisResult,
        job: JobAnalysisResult,
    ) -> list[AnswerEvaluation]:
        evaluations = []
        for q, a in zip(questions, answers):
            eval_result = self.evaluate(q, a, resume, job)
            evaluations.append(eval_result)
        return evaluations


def evaluate_answer(
    question: InterviewQuestion,
    answer: str,
    resume: ResumeAnalysisResult,
    job: JobAnalysisResult,
) -> AnswerEvaluation:
    evaluator = AnswerEvaluator()
    return evaluator.evaluate(question, answer, resume, job)
