import time
from ai_interview_assistant import logger

class ArtifactMonitor:
    """
    Logs performance metrics such as token usage, latency, and system outputs.
    """
    @staticmethod
    def log_latency(operation_name: str, start_time: float):
        latency = time.time() - start_time
        logger.info(f"[MONITOR] {operation_name} completed in {latency:.2f} seconds.")

    @staticmethod
    def log_tokens(model_name: str, prompt_tokens: int, completion_tokens: int):
        logger.info(f"[MONITOR] {model_name} | Prompt: {prompt_tokens} | Completion: {completion_tokens}")