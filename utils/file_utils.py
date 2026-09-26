import hashlib
import mimetypes
import os
from pathlib import Path

from config.settings import settings

try:
    import magic

    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}


def validate_file_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in (settings.allowed_extensions or [])


def validate_file_size(file_path: str) -> bool:
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    return size_mb <= settings.max_file_size_mb


def validate_mime_type(file_path: str, expected_ext: str) -> bool:
    if not HAS_MAGIC:
        return _fallback_mime_check(file_path, expected_ext)

    try:
        mime_type = magic.from_file(file_path, mime=True)
        expected_mime = ALLOWED_MIME_TYPES.get(expected_ext.lower())
        if expected_mime:
            return mime_type == expected_mime
        return True
    except Exception:
        return _fallback_mime_check(file_path, expected_ext)


def _fallback_mime_check(file_path: str, expected_ext: str) -> bool:
    mime_type, _ = mimetypes.guess_type(file_path)
    expected_mime = ALLOWED_MIME_TYPES.get(expected_ext.lower())
    if expected_mime and mime_type:
        return mime_type == expected_mime
    return True


def sanitize_filename(filename: str) -> str:
    name = Path(filename).stem
    ext = Path(filename).suffix
    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
    safe_name = safe_name.replace(" ", "_")
    return f"{safe_name}{ext}"


def compute_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def save_uploaded_file(uploaded_file, upload_dir: str = "./data/uploads") -> tuple[str, str]:
    os.makedirs(upload_dir, exist_ok=True)

    original_name = getattr(uploaded_file, "name", "uploaded_file")
    safe_name = sanitize_filename(original_name)
    file_path = os.path.join(upload_dir, safe_name)

    counter = 1
    base_name = Path(safe_name).stem
    ext = Path(safe_name).suffix
    while os.path.exists(file_path):
        file_path = os.path.join(upload_dir, f"{base_name}_{counter}{ext}")
        counter += 1

    with open(file_path, "wb") as f:
        if hasattr(uploaded_file, "getbuffer"):
            f.write(uploaded_file.getbuffer())
        elif hasattr(uploaded_file, "read"):
            f.write(uploaded_file.read())
        else:
            raise ValueError("Uploaded file must have getbuffer() or read() method")

    return file_path, safe_name


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def is_audio_file(filename: str) -> bool:
    audio_extensions = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
    return get_file_extension(filename) in audio_extensions


def is_document_file(filename: str) -> bool:
    doc_extensions = {".pdf", ".docx", ".txt"}
    return get_file_extension(filename) in doc_extensions


def cleanup_temp_files(file_paths: list) -> None:
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def format_file_size(size_bytes: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
