import os
from pathlib import Path
import logging

# Set up logging to track file creation
logging.basicConfig(level=logging.INFO, format='[%(asctime)s]: %(message)s:')

project_name = "ai_interview_assistant"

list_of_files = [
    ".github/workflows/.gitkeep",
    f"src/{project_name}/__init__.py",
    f"src/{project_name}/logger.py",
    f"src/{project_name}/components/__init__.py",
    f"src/{project_name}/components/data_ingestion.py",
    f"src/{project_name}/components/speech_to_text.py",
    f"src/{project_name}/components/llm_handler.py",
    f"src/{project_name}/components/emotion_detector.py",
    f"src/{project_name}/components/proctoring_engine.py",
    f"src/{project_name}/components/text_to_speech.py",
    f"src/{project_name}/components/question_bank.py",
    f"src/{project_name}/components/prompt_manager.py",
    f"src/{project_name}/components/audio_handler.py",
    f"src/{project_name}/components/artifact_monitors.py",
    f"src/{project_name}/components/behavioral_analyzer.py",
    f"src/{project_name}/components/code_executor.py",
    f"src/{project_name}/utils/__init__.py",
    f"src/{project_name}/utils/common.py",
    f"src/{project_name}/config/__init__.py",
    f"src/{project_name}/config/configuration.py",
    f"src/{project_name}/pipeline/__init__.py",
    f"src/{project_name}/pipeline/interviewer_pipeline.py",
    f"src/{project_name}/entity/__init__.py",
    f"src/{project_name}/constants/__init__.py",
    "config/config.yaml",
    "params.yaml",
    "requirements.txt",
    "setup.py",
    "setup_env.py",
    "test.py",
    "verify_ffmpeg.py",
    "research/trials.ipynb",
    "templates/index.html",
    "app.py",
    "main.py",
    "Dockerfile",
    ".env"
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory; {filedir} for the file: {filename}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
            logging.info(f"Creating empty file: {filepath}")
    else:
        logging.info(f"{filename} already exists")
