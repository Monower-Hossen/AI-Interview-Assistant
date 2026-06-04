import os
from box.exceptions import BoxValueError
import yaml
from ai_interview_assistant import logger
import json
from ensure import ensure_annotations
from box import ConfigBox
from pathlib import Path
from typing import Any, Optional
import time
import subprocess
import shutil
from pypdf import PdfReader

@ensure_annotations
def read_yaml(path_to_yaml: Path) -> ConfigBox:
    """reads yaml file and returns
    Args:
        path_to_yaml (Path): path like input
    Raises:
        ValueError: if yaml file is empty
        e: empty file
    Returns:
        ConfigBox: ConfigBox type
    """
    try:
        with open(path_to_yaml, encoding="utf-8") as yaml_file:
            content = yaml.safe_load(yaml_file)
            if content is None:
                raise ValueError("yaml file is empty")
            logger.info(f"yaml file: {path_to_yaml} loaded successfully")
            return ConfigBox(content)
    except BoxValueError:
        raise ValueError("yaml file is empty")
    except Exception as e:
        raise e

@ensure_annotations
def create_directories(path_to_directories: list, verbose=True):
    """create list of directories
    Args:
        path_to_directories (list): list of path of directories
        ignore_log (bool, optional): ignore if multiple dirs is to be created. Defaults to False.
    """
    for path in path_to_directories:
        os.makedirs(path, exist_ok=True)
        if verbose:
            logger.info(f"created directory at: {path}")

@ensure_annotations
def save_json(path: Path, data: dict):
    """save json data
    Args:
        path (Path): path to json file
        data (dict): data to be saved in json file
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    logger.info(f"json file saved at: {path}")

@ensure_annotations
def get_size(path: Path) -> str:
    """get size in KB
    Args:
        path (Path): path of the file
    Returns:
        str: size in KB
    """
    size_in_kb = round(os.path.getsize(path)/1024)
    return f"~ {size_in_kb} KB"

@ensure_annotations
def clean_directory(path: Path, older_than_seconds: int = 3600):
    """
    Deletes files in a directory that are older than a certain age.
    """
    if not path.exists():
        logger.warning(f"Directory {path} does not exist. Skipping cleanup.")
        return

    try:
        now = time.time()
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path):
                if os.stat(file_path).st_mtime < now - older_than_seconds:
                    os.remove(file_path)
                    logger.info(f"Deleted old file: {file}")
    except Exception as e:
        logger.error(f"Error during directory cleanup: {e}")

@ensure_annotations
def convert_to_wav(input_path: Path, output_path: Path, ffmpeg_path: str = "ffmpeg"):
    """
    Converts input audio to a standard 16kHz mono WAV file using ffmpeg.
    Essential for consistent STT performance.
    """
    resolved_ffmpeg = get_ffmpeg_executable(ffmpeg_path)
    
    if not resolved_ffmpeg:
        logger.error("FFmpeg not found during conversion attempt.")
        raise RuntimeError("FFmpeg is required for audio processing but was not found.")

    try:
        command = [
            resolved_ffmpeg, '-i', str(input_path),
            '-ar', '16000',
            '-ac', '1',
            '-y',  # Overwrite output
            str(output_path)
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Audio converted successfully to: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed: {e.stderr.decode()}")
        raise RuntimeError("Failed to process audio format.")

@ensure_annotations
def get_ffmpeg_executable(ffmpeg_path: str = "ffmpeg") -> Optional[str]:
    """
    Finds the FFmpeg executable path. Searches system PATH and common 
    installation directories (e.g., WinGet on Windows).
    Returns the absolute path if found and verified, else None.
    """
    executable = shutil.which(ffmpeg_path)

    # Validate the found executable; if it fails, proceed to discovery
    if executable:
        try:
            subprocess.run([executable, '-version'], check=True, capture_output=True)
            return str(Path(executable).absolute())
        except Exception:
            executable = None

    if not executable and os.name == 'nt':
        # 0. Direct check for common Windows shims/links (fastest)
        possible_shims = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe'),
            os.path.join(os.environ.get('ProgramFiles', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.environ.get('SystemDrive', 'C:'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'scoop', 'shims', 'ffmpeg.exe')
        ]
        for shim in possible_shims:
            if os.path.exists(shim):
                executable = shim
                break

    if not executable and os.name == 'nt':
        # 1. Try to refresh PATH from Registry (solves stale terminal issues)
        try:
            import winreg
            paths = []
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                    u_path, _ = winreg.QueryValueEx(key, "Path")
                    paths.append(u_path)
            except Exception: pass
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                    s_path, _ = winreg.QueryValueEx(key, "Path")
                    paths.append(s_path)
            except Exception: pass
            
            full_path = os.pathsep.join(paths)
            executable = shutil.which("ffmpeg", path=full_path)
        except Exception:
            pass

    if not executable and os.name == 'nt':
        # 2. Try Windows 'where' command
        try:
            where_res = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
            if where_res.returncode == 0:
                candidate = where_res.stdout.splitlines()[0].strip()
                if os.path.exists(candidate):
                    executable = candidate
        except Exception:
            pass

    if not executable and os.name == 'nt':
        # 2. Expand search bases for common Windows installation patterns
        search_bases = []
        
        # System Drive Root
        sys_drive = os.environ.get('SystemDrive', 'C:')
        search_bases.append(os.path.join(sys_drive, 'ffmpeg'))
        
        # Program Files & ProgramData (Choco/WinGet System)
        for env_var in ['ProgramFiles', 'ProgramFiles(x86)', 'ProgramData']:
            base_path = os.environ.get(env_var)
            if base_path:
                search_bases.extend([
                    os.path.join(base_path, 'ffmpeg', 'bin'),
                    os.path.join(base_path, 'WinGet', 'Packages'),
                    os.path.join(base_path, 'WinGet', 'Links'),
                    os.path.join(base_path, 'chocolatey', 'bin')
                ])

        # User Specific AppData (WinGet User/Scoop)
        local_app_data = os.environ.get('LOCALAPPDATA')
        if local_app_data:
            search_bases.extend([
                os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Links'),
                os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Packages'),
                os.path.join(local_app_data, 'ffmpeg', 'bin'),
            ])
        
        user_profile = os.environ.get('USERPROFILE')
        if user_profile:
            search_bases.append(os.path.join(user_profile, 'scoop', 'shims'))

        for winget_base in search_bases:
            if os.path.exists(winget_base):
                for root, dirs, files in os.walk(winget_base):
                    # Limit depth for performance
                    try:
                        rel_path = os.path.relpath(root, winget_base)
                        if rel_path != '.' and len(Path(rel_path).parts) > 5:
                            dirs[:] = [] # stop recursion 
                            continue
                    except Exception:
                        pass

                    if 'ffmpeg.exe' in files:
                        executable = os.path.join(root, 'ffmpeg.exe')
                        break
                if executable:
                    break

        # Validate the discovered executable
        if executable:
            try:
                subprocess.run([executable, '-version'], check=True, capture_output=True)
                return str(Path(executable).absolute())
            except Exception:
                pass
    
    return None

@ensure_annotations
def is_ffmpeg_installed(ffmpeg_path: str = "ffmpeg") -> bool:
    return get_ffmpeg_executable(ffmpeg_path) is not None

@ensure_annotations
def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extracts text from a PDF file.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise e