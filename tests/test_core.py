from unittest.mock import Mock, patch

import pytest


# Test Resume Analyzer
class TestResumeAnalyzer:
    def test_resume_analysis_result_structure(self):
        from services.resume_analyzer import ResumeAnalysisResult

        result = ResumeAnalysisResult(
            candidate_name="John Doe",
            email="john@example.com",
            skills=["Python", "SQL"],
            programming_languages=["Python"],
            frameworks=["FastAPI"],
            databases=["PostgreSQL"],
            tools=["Git", "Docker"],
            projects=[],
            certifications=[],
            education=[],
            experience=[],
        )

        assert result.candidate_name == "John Doe"
        assert result.email == "john@example.com"
        assert "Python" in result.skills

    def test_resume_scores_validation(self):
        from services.resume_analyzer import ResumeScores

        scores = ResumeScores(
            technical_skills=85.0,
            experience=70.0,
            projects=90.0,
            education=80.0,
            certifications=60.0,
            structure=75.0,
            overall=78.0,
        )

        assert scores.overall == 78.0
        assert 0 <= scores.technical_skills <= 100


# Test Job Analyzer
class TestJobAnalyzer:
    def test_job_analysis_result_structure(self):
        from services.job_analyzer import JobAnalysisResult

        result = JobAnalysisResult(
            job_title="Software Engineer",
            company="Tech Corp",
            required_skills=["Python", "AWS"],
            preferred_skills=["Docker"],
            programming_languages=["Python"],
            frameworks=["FastAPI"],
            databases=["PostgreSQL"],
            tools=["Git"],
            experience_requirements=["3+ years"],
            education_requirements=["BS Computer Science"],
            responsibilities=["Build APIs"],
            keywords=["python", "aws", "api"],
        )

        assert result.job_title == "Software Engineer"
        assert "Python" in result.required_skills


# Test Job Matcher
class TestJobMatcher:
    def test_match_result_structure(self):
        from services.job_matcher import MissingSkill, ResumeJobMatchResult, SkillMatch

        match = ResumeJobMatchResult(
            technical_skills_match=80.0,
            experience_match=70.0,
            projects_match=90.0,
            education_match=85.0,
            overall_match=81.0,
            matching_skills=[
                SkillMatch(
                    skill="Python",
                    resume_evidence="5 years",
                    job_requirement="Python required",
                    match_strength="strong",
                )
            ],
            missing_skills=[
                MissingSkill(
                    skill="Docker",
                    job_requirement="Containerization",
                    importance="important",
                )
            ],
            skill_gaps=["Docker", "Kubernetes"],
            experience_gaps=[],
            recommendations=["Learn Docker"],
        )

        assert match.overall_match == 81.0
        assert len(match.matching_skills) == 1
        assert len(match.missing_skills) == 1


# Test Interview Generator
class TestInterviewGenerator:
    def test_question_structure(self):
        from services.interview_generator import (
            Difficulty,
            InterviewQuestion,
            QuestionCategory,
        )

        question = InterviewQuestion(
            question_number=1,
            category=QuestionCategory.TECHNICAL,
            difficulty=Difficulty.MEDIUM,
            question_text="Explain Python decorators",
            expected_key_points=["Function wrapping", "@ syntax", "Use cases"],
            follow_up_hints=["Ask about functools.wraps", "Ask about class decorators"],
        )

        assert question.question_number == 1
        assert question.category == QuestionCategory.TECHNICAL
        assert question.difficulty == Difficulty.MEDIUM

    def test_question_set(self):
        from services.interview_generator import (
            Difficulty,
            InterviewQuestion,
            QuestionCategory,
            QuestionSet,
        )

        questions = [
            InterviewQuestion(
                question_number=1,
                category=QuestionCategory.TECHNICAL,
                difficulty=Difficulty.EASY,
                question_text="Q1",
                expected_key_points=[],
            ),
            InterviewQuestion(
                question_number=2,
                category=QuestionCategory.HR,
                difficulty=Difficulty.EASY,
                question_text="Q2",
                expected_key_points=[],
            ),
        ]

        qset = QuestionSet(
            questions=questions,
            total_count=2,
            category_distribution={"technical": 1, "hr": 1},
        )

        assert qset.total_count == 2
        assert len(qset.questions) == 2

    def test_question_set_coerces_sparse_questions(self):
        from services.interview_generator import QuestionSet

        qset = QuestionSet.model_validate(
            {
                "questions": [
                    {"question": "Explain FastAPI DI"},
                    {
                        "question_text": "Walk me through a project",
                        "category": "Project Based",
                        "expected_key_points": "architecture",
                    },
                ]
            }
        )

        assert qset.total_count == 2
        assert qset.questions[0].question_number == 1
        assert qset.questions[0].difficulty.value == "medium"
        assert qset.questions[1].category.value == "project_based"
        assert qset.questions[1].expected_key_points == ["architecture"]
        assert qset.category_distribution == {"technical": 1, "project_based": 1}

    def test_question_generator_retry_prompt_has_no_format_error(self):
        from services.interview_generator import (
            InterviewGenerator,
            QuestionSet,
        )
        from services.job_analyzer import JobAnalysisResult
        from services.job_matcher import ResumeJobMatchResult
        from services.resume_analyzer import ResumeAnalysisResult

        generator = InterviewGenerator.__new__(InterviewGenerator)
        generator.llm = Mock()

        calls = []

        def fake_structured(prompt, response_model, **kwargs):
            calls.append(prompt)
            if len(calls) == 1:
                raise RuntimeError("primary prompt failed")
            return QuestionSet(questions=[], total_count=0, category_distribution={})

        generator.llm.generate_structured.side_effect = fake_structured

        match = ResumeJobMatchResult(
            technical_skills_match=50.0,
            experience_match=50.0,
            projects_match=50.0,
            education_match=50.0,
            overall_match=50.0,
        )

        result = generator.generate(
            ResumeAnalysisResult(),
            JobAnalysisResult(),
            match,
            total_questions=3,
        )

        assert len(calls) == 2
        assert "3 interview questions" in calls[1]
        assert "{total_questions}" not in calls[1]
        assert result.total_count == 0



# Test Answer Evaluator
class TestAnswerEvaluator:
    def test_evaluation_structure(self):
        from services.answer_evaluator import AnswerEvaluation

        eval_result = AnswerEvaluation(
            technical_accuracy=8.0,
            relevance=9.0,
            communication=7.0,
            confidence=8.0,
            completeness=7.5,
            overall_score=7.9,
            strengths=["Good technical knowledge"],
            weaknesses=["Could elaborate more"],
            missing_points=["Time complexity"],
            incorrect_points=[],
            suggested_answer="Better answer...",
            communication_feedback="Clear but concise",
            technical_feedback="Accurate",
        )

        assert eval_result.overall_score == 7.9
        assert 0 <= eval_result.technical_accuracy <= 10


# Test Report Generator
class TestReportGenerator:
    def test_report_structure(self):
        from services.report_generator import ImprovementPlanItem, InterviewReport

        report = InterviewReport(
            overall_score=7.5,
            technical_score=7.8,
            communication_score=7.0,
            hr_score=8.0,
            problem_solving_score=7.2,
            strengths=["Strong technical skills"],
            weaknesses=["Communication needs work"],
            frequently_missed_concepts=["System design"],
            recommended_topics=["Distributed systems"],
            recommended_projects=["Build a microservice"],
            recommended_questions=["Practice system design"],
            improvement_plan_7_day=[
                ImprovementPlanItem(
                    day=1,
                    focus="System Design",
                    activity="Study CAP theorem",
                    resources=["DDIA book"],
                    estimated_hours=2,
                )
            ],
            improvement_plan_30_day=[
                ImprovementPlanItem(
                    day=1,
                    focus="Week 1",
                    activity="System design basics",
                    resources=[],
                    estimated_hours=10,
                )
            ],
        )

        assert report.overall_score == 7.5
        assert len(report.improvement_plan_7_day) == 1


# Test Utilities
class TestUtilities:
    def test_clean_text(self):
        from utils.helpers import clean_text

        text = "  Hello    World\n\n\nTest  "
        cleaned = clean_text(text)
        assert cleaned == "Hello World\n\nTest"

    def test_extract_email(self):
        from utils.helpers import extract_email

        text = "Contact me at john.doe@example.com for more info"
        email = extract_email(text)
        assert email == "john.doe@example.com"

    def test_extract_phone(self):
        from utils.helpers import extract_phone

        text = "Call me at +1-555-123-4567"
        phone = extract_phone(text)
        assert phone is not None

    def test_deduplicate_skills(self):
        from utils.helpers import deduplicate_skills

        skills = ["Python", "python", "PYTHON", "Java", "java"]
        deduped = deduplicate_skills(skills)
        assert len(deduped) == 2
        assert "Python" in deduped
        assert "Java" in deduped

    def test_safe_json_parse(self):
        from utils.helpers import safe_json_parse

        result = safe_json_parse('{"key": "value"}')
        assert result == {"key": "value"}

        result = safe_json_parse("invalid json")
        assert result is None

    def test_calculate_percentage(self):
        from utils.helpers import calculate_percentage

        assert calculate_percentage(75, 100) == 75.0
        assert calculate_percentage(0, 100) == 0.0
        assert calculate_percentage(50, 0) == 0.0


# Test File Utils
class TestFileUtils:
    def test_validate_extension(self):
        from utils.file_utils import validate_file_extension

        assert validate_file_extension("test.pdf") == True
        assert validate_file_extension("test.docx") == True
        assert validate_file_extension("test.txt") == True
        assert validate_file_extension("test.exe") == False

    def test_sanitize_filename(self):
        from utils.file_utils import sanitize_filename

        assert sanitize_filename("My Resume.pdf") == "My_Resume.pdf"
        assert sanitize_filename("test@#$%.docx") == "test.docx"

    def test_get_file_extension(self):
        from utils.file_utils import get_file_extension

        assert get_file_extension("test.PDF") == ".pdf"
        assert get_file_extension("test.Docx") == ".docx"

    def test_is_audio_file(self):
        from utils.file_utils import is_audio_file

        assert is_audio_file("test.wav") == True
        assert is_audio_file("test.mp3") == True
        assert is_audio_file("test.pdf") == False

    def test_is_document_file(self):
        from utils.file_utils import is_document_file

        assert is_document_file("test.pdf") == True
        assert is_document_file("test.docx") == True
        assert is_document_file("test.mp3") == False


# Test RAG Components
class TestRAGComponents:
    @patch("rag.document_loader.pypdf.PdfReader")
    def test_pdf_loader(self, mock_reader):
        from rag.document_loader import PDFLoader

        mock_page = Mock()
        mock_page.extract_text.return_value = "Test content"
        mock_reader.return_value.pages = [mock_page]

        loader = PDFLoader()
        assert loader.supports("test.pdf") == True
        assert loader.supports("test.docx") == False

    def test_text_splitter(self):
        from rag.text_splitter import TextChunk, TextSplitter

        splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
        chunks = splitter.split_text("This is a test. " * 20, metadata={}, source="test")

        assert len(chunks) > 0
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_embedding_model_singleton(self):
        from rag.embeddings import get_embedding_model

        model1 = get_embedding_model()
        model2 = get_embedding_model()

        assert model1 is model2  # Singleton
        assert model1.dimension > 0


# Test Database Models
class TestDatabaseModels:
    def test_user_session_model(self):
        from database.models import UserSession

        session = UserSession(session_id="test123")
        assert session.session_id == "test123"

    def test_resume_analysis_model(self):
        from database.models import ResumeAnalysis

        resume = ResumeAnalysis(
            session_id=1,
            file_name="test.pdf",
            candidate_name="John Doe",
            overall_resume_score=85.0,
        )

        assert resume.candidate_name == "John Doe"
        assert resume.overall_resume_score == 85.0


class TestMultiProvider:
    """Test multi-provider LLM service with fallback."""

    def test_provider_chain_auto(self):
        from config.settings import settings

        settings.llm_provider = "auto"
        settings.gemini_api_key = "fake-gemini-key"
        settings.mistral_api_key = "fake-mistral-key"
        settings.groq_api_key = "fake-groq-key"
        settings.provider_priority = "groq,gemini,mistral"

        from services.llm_service import LLMService

        service = LLMService()
        names = [p.get_provider_name() for p in service.providers]
        assert names == ["groq", "gemini", "mistral"]

    def test_provider_chain_forced(self):
        import os as _os

        from config.settings import settings

        _os.environ["LLM_PROVIDER"] = "groq"
        settings.llm_provider = "groq"
        settings.gemini_api_key = "fake-gemini-key"
        settings.mistral_api_key = "fake-mistral-key"
        settings.groq_api_key = "fake-groq-key"

        from services.llm_service import LLMService

        service = LLMService()
        names = [p.get_provider_name() for p in service.providers]
        assert names[0] == "groq"
        assert "gemini" in names and "mistral" in names

    def test_no_providers_raises(self):
        import os as _os

        from config.settings import settings

        _os.environ["LLM_PROVIDER"] = "auto"
        settings.llm_provider = "auto"
        settings.gemini_api_key = ""
        settings.mistral_api_key = ""
        settings.groq_api_key = ""

        from services.llm_service import LLMService

        with pytest.raises(ValueError, match="No LLM providers"):
            LLMService()

    def test_error_classification(self):
        import httpx

        from services.llm_service import (
            is_api_key_error,
            is_auth_error,
            is_rate_limit_error,
            is_retryable_error,
        )

        req = httpx.Request("POST", "https://api.test/v1/chat/completions")
        resp429 = httpx.Response(status_code=429)
        resp401 = httpx.Response(status_code=401)
        resp500 = httpx.Response(status_code=500)

        exc_429 = httpx.HTTPStatusError("rate limit", request=req, response=resp429)
        exc_401 = httpx.HTTPStatusError("unauthorized", request=req, response=resp401)
        exc_500 = httpx.HTTPStatusError("server error", request=req, response=resp500)

        assert is_rate_limit_error(exc_429)
        assert not is_rate_limit_error(exc_500)

        assert is_auth_error(exc_401)
        assert not is_auth_error(exc_500)

        assert is_retryable_error(exc_500)
        assert not is_retryable_error(exc_401)

        assert is_api_key_error(ValueError("Gemini API key not provided"))
        assert not is_api_key_error(exc_401)

    def test_structured_output_coercion(self):
        """Test that string project entries are coerced to ProjectItem dicts."""
        from services.resume_analyzer import ResumeAnalysisWithScores

        data = {
            "analysis": {
                "candidate_name": "John",
                "projects": ["Project A", "Project B"],
                "experience": ["Job 1", "Job 2"],
                "education": ["BS Computer Science"],
            },
            "scores": {
                "technical_skills": 85,
                "experience": 75,
                "projects": 80,
                "education": 90,
                "certifications": 0,
                "structure": 70,
                "overall": 76,
            },
        }

        result = ResumeAnalysisWithScores.model_validate(data)
        assert len(result.analysis.projects) == 2
        assert result.analysis.projects[0].name == "Project A"
        assert len(result.analysis.experience) == 2
        assert result.analysis.experience[0].title == "Job 1"
        assert len(result.analysis.education) == 1
        assert result.analysis.education[0].degree == "BS Computer Science"

    def test_missing_scores_defaults_to_empty(self):
        """Test that missing scores field doesn't cause ValidationError."""
        from services.resume_analyzer import ResumeAnalysisWithScores

        data = {
            "analysis": {
                "candidate_name": "Jane",
                "projects": [],
            }
        }

        result = ResumeAnalysisWithScores.model_validate(data)
        assert result.scores is None  # Optional field

    def test_single_education_item_is_coerced(self):
        from services.resume_analyzer import ResumeAnalysisWithScores

        result = ResumeAnalysisWithScores.model_validate(
            {"degree": "BSc Computer Science", "institution": "Example University"}
        )

        assert result.analysis.education[0].degree == "BSc Computer Science"
        assert result.analysis.education[0].institution == "Example University"

    def test_empty_malformed_response_gets_empty_analysis(self):
        from services.resume_analyzer import ResumeAnalysisWithScores

        result = ResumeAnalysisWithScores.model_validate({})

        assert result.analysis.skills == []
        assert result.scores is None


class TestDatabaseSessions:
    def test_rows_stay_readable_after_context_closes(self, tmp_path):
        import database.db as db_module
        from config.settings import settings
        from database.models import UserSession

        original_path = settings.database_path
        settings.database_path = str(tmp_path / "sessions.db")
        db_module.engine = None
        db_module.SessionLocal = None

        try:
            db_module.init_database()

            with db_module.get_db_context() as db:
                row = UserSession(session_id="abc12345")
                db.add(row)
                db.flush()
                row_id = row.id

            assert row.session_id == "abc12345"
            assert row.id == row_id
            assert row.created_at is not None

            with db_module.get_db_context() as db:
                loaded = (
                    db.query(UserSession).filter(UserSession.session_id == "abc12345").first()
                )
                assert loaded is not None

            assert loaded.id == row_id
        finally:
            db_module.close_database()
            db_module.SessionLocal = None
            settings.database_path = original_path

    def test_failed_context_rolls_back_and_leaves_readable(self, tmp_path):
        import database.db as db_module
        from config.settings import settings
        from database.models import UserSession

        original_path = settings.database_path
        settings.database_path = str(tmp_path / "rollback.db")
        db_module.engine = None
        db_module.SessionLocal = None

        try:
            db_module.init_database()

            with pytest.raises(RuntimeError), db_module.get_db_context() as db:
                db.add(UserSession(session_id="rolled-back"))
                db.flush()
                raise RuntimeError("boom")

            with db_module.get_db_context() as db:
                count = db.query(UserSession).filter(UserSession.session_id == "rolled-back").count()

            assert count == 0
        finally:
            db_module.close_database()
            db_module.SessionLocal = None
            settings.database_path = original_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
