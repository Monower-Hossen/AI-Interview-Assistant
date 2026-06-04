import sys

def main():
    try:
        # Import logger first to provide immediate feedback to the user
        from ai_interview_assistant import logger
        logger.info("Starting AI Interview Assistant...")
        
        # Deferred imports help avoid "silent hangs" during the heavy loading 
        # phase of AI libraries like LangChain, Pydantic, and Groq.
        logger.info("Loading AI components and dependencies (this may take a moment)...")
        from ai_interview_assistant.pipeline.interviewer_pipeline import InterviewerPipeline
        
        pipeline = InterviewerPipeline()
        
        logger.info("Pipeline initialized successfully.")
        print("To start the web interface, run: python app.py")
        
    except KeyboardInterrupt:
        print("\n[INFO] Startup cancelled by user.")
        sys.exit(0)
    except Exception as e:
        from ai_interview_assistant import logger
        logger.exception(e)
        sys.exit(1)

if __name__ == "__main__":
    main()