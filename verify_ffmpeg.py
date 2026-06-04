import sys
import os
from pathlib import Path

# Add src to path so we can import our utilities
sys.path.append(str(Path(__file__).parent / "src"))

from ai_interview_assistant.utils.common import get_ffmpeg_executable
import shutil

def verify():
    print("--- FFmpeg Diagnostic ---")
    
    # 1. Standard Path Check
    standard_path = shutil.which("ffmpeg")
    print(f"Standard PATH search: {standard_path if standard_path else 'NOT FOUND'}")

    # 2. Project Discovery Check
    discovered_path = get_ffmpeg_executable()
    print(f"Project discovery logic: {discovered_path if discovered_path else 'NOT FOUND'}")

    if discovered_path:
        print(f"\nSUCCESS: FFmpeg is recognized at: {discovered_path}")
    else:
        print("\nFAILURE: FFmpeg is not recognized. Please run 'python setup_env.py' as Administrator.")

if __name__ == "__main__":
    verify()