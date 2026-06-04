import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ai_interview_assistant.entity import LLMConfig

# Load environment variables from .env file
load_dotenv()

class LLMHandler:
    def __init__(self, config: LLMConfig):
        self.config = config
        # Initialize the free Groq LLM using configuration values
        self.llm = ChatGroq(
            model=self.config.model_name, 
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        # Dictionary to store chat history for different sessions
        self.sessions = {} 

    def _get_session_history(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def generate_initial_question(self, session_id: str = "default", job_role: str = "Software Engineer", resume_text: str = "", language: str = "bn", role_config: dict = None) -> str:
        """Initializes the conversation with the system prompt and asks the first question."""
        history = self._get_session_history(session_id)
        
        system_prompt = self.config.prompt_template.format(job_role=job_role)
        if language == "en":
            # Adjust system instructions for English
            system_prompt = system_prompt.replace("বাংলা ভাষায় (Bengali)", "English")
            system_prompt = system_prompt.replace("বাংলায়", "English")
            
        if resume_text:
            system_prompt += f"\n\nCandidate's Resume Information:\n{resume_text}"

        if role_config and role_config.get("topics"):
            topics_str = ", ".join(role_config["topics"])
            system_prompt += f"\n\nFocus areas for this interview: {topics_str}"
        
        history.append(SystemMessage(content=system_prompt))
        
        # Initial greeting and first question prompt
        prompt = f"বাংলায় নিজের পরিচয় দিন এবং {job_role} পজিশনের জন্য ইন্টারভিউ শুরু করুন। প্রথম প্রশ্নটি জিজ্ঞাসা করুন।" if language == "bn" else f"Introduce yourself and start the interview for the {job_role} position. Ask the first question."
        history.append(HumanMessage(content=prompt))
        
        response = self.llm.invoke(history)
        history.append(AIMessage(content=response.content))
        return response.content

    def generate_role_config(self, job_role: str, experience_level: str = "Professional") -> dict:
        """Generates a dynamic technical profile for a new job role."""
        prompt = f"""
        Generate a structured interview configuration for the role of '{job_role}' at '{experience_level}' level.
        Provide a list of 5 core technical topics and 3 sample questions.
        Return only valid JSON in this format: {{"topics": ["topic1", "topic2"], "sample_questions": ["q1", "q2"]}}
        """
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            # Basic cleaning to ensure valid JSON extraction if LLM wraps it in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"Error generating dynamic role config: {e}")
            return {"error": str(e), "topics": [], "sample_questions": []}

    def get_response(self, user_input: str, session_id: str = "default", job_role: str = "Software Engineer", resume_text: str = "", language: str = "bn") -> str:
        """Processes user input and returns the AI interviewer's next response/question."""
        history = self._get_session_history(session_id)
        
        if not history:
            return self.generate_initial_question(session_id, job_role, resume_text, language)

        if user_input.strip():
            history.append(HumanMessage(content=user_input))

        try:
            response = self.llm.invoke(history)
            history.append(AIMessage(content=response.content))
            return response.content
        except Exception as e:
            return f"Error communicating with LLM: {str(e)}"

    def clear_session_memory(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def generate_feedback(self, session_id: str) -> str:
        history = self._get_session_history(session_id)
        
        # Using a more structured prompt for professional feedback
        feedback_prompt = (
            "The interview session has concluded. Acting as a Senior Lead Interviewer, "
            "provide a professional performance report. Include a scoring table for "
            "Technical Skills, Soft Skills, and Overall Fit. Suggest whether the candidate "
            "should be 'Hired', 'Follow-up Required', or 'Rejected'."
        )
        temp_history = history + [HumanMessage(content=feedback_prompt)]
        response = self.llm.invoke(temp_history)
        return response.content