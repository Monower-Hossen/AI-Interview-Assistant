import json
import re
from datetime import datetime
from typing import Any


def safe_json_parse(text: str, default: Any = None) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def extract_json_from_text(text: str) -> dict | None:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    parsed = safe_json_parse(cleaned)
    if isinstance(parsed, dict):
        return parsed

    try:
        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    stripped = cleaned.lstrip()
    if stripped.startswith(('"', "'")):
        wrapped = "{" + cleaned + "}"
        parsed = safe_json_parse(wrapped)
        if isinstance(parsed, dict):
            return parsed

    start = cleaned.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    outer_start = -1
    outer_end = -1
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                outer_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and outer_start != -1:
                outer_end = i
                candidate = cleaned[outer_start : outer_end + 1]
                parsed = safe_json_parse(candidate)
                if isinstance(parsed, dict):
                    return parsed
                break

    json_pattern = r"\{[\s\S]*?\}"
    matches = re.findall(json_pattern, text)
    matches.sort(key=len, reverse=True)
    for match in matches:
        parsed = safe_json_parse(match)
        if isinstance(parsed, dict):
            return parsed

    stripped = text.lstrip()
    if stripped.startswith(('"', "'")):
        wrapped = "{" + text.strip() + "}"
        parsed = safe_json_parse(wrapped)
        if isinstance(parsed, dict):
            return parsed

    return None


def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def truncate_text(text: str, max_length: int = 4000, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def compact_text(
    text: str,
    max_length: int,
    marker: str = " ... [content omitted] ... ",
) -> str:
    if max_length <= 0:
        return ""

    cleaned = " ".join(text.split())
    if len(cleaned) <= max_length:
        return cleaned
    if len(marker) >= max_length:
        return cleaned[:max_length]

    tail_length = min(max_length // 4, 600)
    head_length = max_length - tail_length - len(marker)
    if head_length <= 0:
        return cleaned[:max_length]

    return f"{cleaned[:head_length].rstrip()}" f"{marker}" f"{cleaned[-tail_length:].lstrip()}"


def extract_email(text: str) -> str | None:
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None


def extract_phone(text: str) -> str | None:
    pattern = r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None


def extract_urls(text: str) -> list[str]:
    pattern = r"https?://[^\s]+"
    return re.findall(pattern, text)


def extract_linkedin(text: str) -> str | None:
    urls = extract_urls(text)
    for url in urls:
        if "linkedin.com" in url.lower():
            return url
    return None


def extract_github(text: str) -> str | None:
    urls = extract_urls(text)
    for url in urls:
        if "github.com" in url.lower():
            return url
    return None


def extract_portfolio(text: str) -> str | None:
    urls = extract_urls(text)
    for url in urls:
        if any(
            keyword in url.lower() for keyword in ["portfolio", "website", "personal", "about.me"]
        ):
            return url
    return None


def normalize_skill(skill: str) -> str:
    skill = skill.strip().lower()
    skill = re.sub(r"[^\w\s+#.-]", "", skill)
    skill = re.sub(r"\s+", " ", skill)
    return skill.title()


def deduplicate_skills(skills: list[str]) -> list[str]:
    seen = set()
    result = []
    for skill in skills:
        normalized = normalize_skill(skill)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def calculate_percentage(value: float, total: float) -> float:
    if total == 0:
        return 0.0
    return round((value / total) * 100, 2)


def format_score(score: float, max_score: float = 10.0) -> str:
    return f"{score:.1f}/{max_score:.1f}"


def get_score_category(score: float) -> str:
    if score >= 9:
        return "Excellent"
    elif score >= 7:
        return "Good"
    elif score >= 5:
        return "Average"
    elif score >= 3:
        return "Below Average"
    else:
        return "Needs Improvement"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def generate_session_id() -> str:
    import uuid

    return str(uuid.uuid4())[:8]


def get_current_timestamp() -> str:
    return datetime.now().isoformat()


def parse_timestamp(timestamp_str: str) -> datetime | None:
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    return None


def merge_dicts(dict1: dict, dict2: dict) -> dict:
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
