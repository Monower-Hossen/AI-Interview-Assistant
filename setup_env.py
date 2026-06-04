import os
import sys
import subprocess
import shutil
import platform

def run_command(command):
    try:
        subprocess.run(command, check=True, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}. Error: {e}")
        return False

def install_ffmpeg():
    """Detects OS and installs FFmpeg if not present."""
    if shutil.which("ffmpeg"):
        print("[INFO] FFmpeg is already installed and in PATH.")
        return True

    print("[INFO] FFmpeg not found. Attempting to install...")
    os_type = platform.system()
    
    if os_type == "Windows":
        print("[INFO] Using winget to install FFmpeg...")
        success = run_command("winget install ffmpeg")
        if not success:
            print("[ERROR] Winget failed. Please download FFmpeg from https://www.gyan.dev/ffmpeg/builds/")
            print("Extract it and add the 'bin' folder to your System PATH manually.")
        return success

    elif os_type == "Darwin": # macOS
        print("[INFO] Using Homebrew to install FFmpeg...")
        return run_command("brew install ffmpeg")
    elif os_type == "Linux":
        print("[INFO] Using apt to install FFmpeg...")
        return run_command("sudo apt-get update && sudo apt-get install -y ffmpeg")
    else:
        print(f"[ERROR] Unsupported OS: {os_type}. Please install FFmpeg manually.")
        return False

def install_python_dependencies():
    """Installs the project in editable mode which handles requirements.txt."""
    print("[INFO] Installing Python dependencies...")
    return run_command(f"{sys.executable} -m pip install -e .")

def create_env_template():
    """Creates a template .env file if it doesn't exist."""
    if not os.path.exists(".env"):
        print("[INFO] Creating .env file template...")
        with open(".env", "w") as f:
            f.write("GROQ_API_KEY=your_api_key_here\n")
        print("[SUCCESS] .env file created. Please update it with your Groq API key.")
    else:
        print("[INFO] .env file already exists.")

if __name__ == "__main__":
    print("=== AI Interview Assistant Environment Setup ===")
    
    ffmpeg_success = install_ffmpeg()
    deps_success = install_python_dependencies()
    create_env_template()
    
    if ffmpeg_success and deps_success:
        print("\n[SUCCESS] Setup completed successfully!")
        print("Please restart your IDE or terminal to ensure FFmpeg is recognized in the PATH.")
        print("Run the application using: python app.py")
    else:
        print("\n[WARNING] Setup completed with errors. Check the logs above.")
    print("===============================================")