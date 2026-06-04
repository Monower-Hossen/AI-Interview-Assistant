import os
import sys
import logging

# Define the logging format: [Timestamp: Level: Module: Message]
logging_str = "[%(asctime)s: %(levelname)s: %(module)s: %(message)s]"

# Define log directory and file path
log_dir = "logs"
log_filepath = os.path.join(log_dir, "running_logs.log")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=logging_str,

    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create the logger instance
logger = logging.getLogger("ai_interview_assistant_logger")
