import os
from ai_interview_assistant.config.configuration import ConfigurationManager
from ai_interview_assistant.components.llm_handler import LLMHandler
from ai_interview_assistant.components.text_to_speech import TextToSpeech
from ai_interview_assistant import logger
from pathlib import Path

def test_components():
    """
    A test script to verify that core components are working correctly.
    This script tests Configuration loading, LLM interaction, and Text-to-Speech.
    """
    try:
        # 1. Test Configuration Manager
        logger.info("Step 1: Testing ConfigurationManager...")
        config_manager = ConfigurationManager()
        llm_config = config_manager.get_llm_config()
        artifacts_config = config_manager.get_artifacts_config()
        logger.info("ConfigurationManager: SUCCESS")

        # 2. Test LLM Handler
        logger.info("Step 2: Testing LLMHandler...")
        llm_handler = LLMHandler(llm_config)
        
        # Testing the initial question generation for a specific role
        job_role = "Python Developer"
        response = llm_handler.generate_initial_question(job_role=job_role)
        print(f"\n[AI Interviewer for {job_role}]: {response}\n")
        logger.info("LLMHandler: SUCCESS")

        # 3. Test Text To Speech
        logger.info("Step 3: Testing TextToSpeech...")
        tts_config = config_manager.get_tts_config()
        tts = TextToSpeech(tts_config)
        output_path = artifacts_config.audio_store / "test_output.mp3"
        tts.generate_speech(response, output_path)
        print(f"Audio file generated at: {output_path}")
        logger.info("TextToSpeech: SUCCESS")

        logger.info("All core components initialized and tested successfully!")

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        # Raising the error to see the full traceback in terminal
        raise e

if __name__ == "__main__":
    test_components()