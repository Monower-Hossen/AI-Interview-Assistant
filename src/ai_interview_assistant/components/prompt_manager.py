class PromptManager:
    """
    Manages system prompts, interview personas, and evaluation rubrics.
    """
    def __init__(self):
        self.personas = {
            "technical": "You are a senior software engineer conducting a technical screening.",
            "behavioral": "You are an HR manager focusing on cultural fit and soft skills."
        }

    def get_interview_prompt(self, job_role: str, language: str = "bn") -> str:
        base_prompt = (
            "আপনি একজন দক্ষ AI টেকনিক্যাল ইন্টারভিউয়ার। {job_role} পজিশনের জন্য একটি পেশাদার ইন্টারভিউ পরিচালনা করুন। "
            "সম্পূর্ণ ইন্টারভিউটি বাংলা ভাষায় (Bengali) গ্রহণ করুন।"
        )
        if language == "en":
            return f"You are an expert AI interviewer. Conduct a professional interview for a {job_role} position in English."
        return base_prompt.format(job_role=job_role)

    def get_evaluation_rubric(self) -> str:
        return """
        Evaluate the candidate on a scale of 1-10 for the following categories:
        1. Technical Accuracy: Correctness of technical answers.
        2. Communication Clarity: Ability to explain complex ideas simply.
        3. Confidence Level: Tone and certainty in responses.
        4. Problem Solving: Logical approach to challenges.
        
        Provide the final evaluation in a structured format with a 'Scorecard' section 
        and a 'Detailed Feedback' section. Mention specific strengths and areas for improvement.
        """