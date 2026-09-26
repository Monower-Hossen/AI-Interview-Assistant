import os
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from config.settings import settings
from utils.helpers import extract_json_from_text, safe_json_parse

T = TypeVar("T", bound=BaseModel)


class GeminiAPIError(Exception):
    pass


class MistralAPIError(Exception):
    pass


class GroqAPIError(Exception):
    pass


def is_api_key_error(exc: BaseException) -> bool:
    msg = str(exc)
    return (
        "API key" in msg
        or "api key" in msg
        or isinstance(exc, (GeminiAPIError, MistralAPIError, GroqAPIError))
    )


def is_auth_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (401, 403) if exc.response else False
    return False


def is_rate_limit_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 if exc.response else False
    if isinstance(exc, (GeminiAPIError, MistralAPIError, GroqAPIError)):
        msg = str(exc).lower()
        return "rate limit" in msg or "429" in msg
    return False


def is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code if exc.response else 0
        return status in _RETRYABLE_STATUS_CODES
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


def is_payload_too_large_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 413 if exc.response else False

    msg = str(exc).lower()
    return (
        "http 413" in msg
        or "request entity too large" in msg
        or "request too large" in msg
        or "payload too large" in msg
    )


def _error_message(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code if exc.response is not None else "unknown"
        try:
            data = exc.response.json()
            detail = data.get("error", {}).get("message") or data.get("detail") or str(exc)
        except Exception:
            detail = exc.response.text.strip() if exc.response is not None else str(exc)
        return f"HTTP {status}: {detail}"
    return str(exc)


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: dict | None = None
    latency_ms: float = 0.0


_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
_MAX_RETRY_AFTER = 120.0
_MAX_RATE_LIMIT_RETRIES = 1
_SHORT_RATE_LIMIT_RETRY = 5.0
_DEFAULT_RATE_LIMIT_COOLDOWN = 30.0
_RATE_LIMIT_BUFFER = 1.0
_request_lock = threading.RLock()
_rate_limit_lock = threading.RLock()


def _retry_after_seconds(response: httpx.Response | None) -> float | None:
    if response is None:
        return None

    value = response.headers.get("retry-after", "").strip()
    if value:
        try:
            return max(0.0, min(float(value), _MAX_RETRY_AFTER))
        except ValueError:
            pass

        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(
                0.0,
                min(
                    (retry_at - datetime.now(UTC)).total_seconds(),
                    _MAX_RETRY_AFTER,
                ),
            )
        except (TypeError, ValueError, OverflowError):
            pass

    value = response.headers.get("retry-after-ms", "").strip()
    if value:
        try:
            return max(0.0, min(float(value) / 1000.0, _MAX_RETRY_AFTER))
        except ValueError:
            pass

    value = response.headers.get("x-ratelimit-reset-after", "").strip()
    if value:
        try:
            return max(0.0, min(float(value), _MAX_RETRY_AFTER))
        except ValueError:
            pass

    value = response.headers.get("x-ratelimit-reset-ms", "").strip()
    if value:
        try:
            return max(0.0, min(float(value) / 1000.0, _MAX_RETRY_AFTER))
        except ValueError:
            pass

    value = response.headers.get("x-ratelimit-reset", "").strip()
    if value:
        try:
            reset_at = float(value)
            if reset_at > 10_000_000_000:
                reset_at /= 1000.0
            return max(0.0, min(reset_at - time.time(), _MAX_RETRY_AFTER))
        except ValueError:
            pass

    return None


def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
    retry_after = _retry_after_seconds(response)
    if retry_after is not None:
        delay = retry_after
    else:
        delay = min(
            settings.retry_backoff_factor * (2**attempt),
            _MAX_RETRY_AFTER,
        )

    jitter = random.uniform(0.0, min(delay * 0.25, 1.0))
    return min(delay + jitter, _MAX_RETRY_AFTER)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(self, prompt: str, response_model: type[T], **kwargs) -> T:
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        raise NotImplementedError


class _HTTPProvider(LLMProvider):
    provider_name = ""
    default_timeout = 30
    supports_json_mode = True

    def __init__(self, api_key: str, model: str, base_url: str):
        if not api_key:
            raise ValueError(f"{self.provider_name.title()} API key not provided")

        timeout = httpx.Timeout(
            connect=10.0,
            read=float(getattr(settings, "request_timeout", self.default_timeout)),
            write=15.0,
            pool=10.0,
        )
        self.model = model
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    def _post(self, path: str, payload: dict) -> httpx.Response:
        global _last_request_time
        max_attempts = max(1, int(getattr(settings, "max_retries", 3)) + 1)

        with _request_lock:
            for attempt in range(max_attempts):
                now = time.time()
                elapsed = now - _last_request_time
                if elapsed < _MIN_REQUEST_INTERVAL:
                    time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
                _last_request_time = time.time()

                try:
                    response = self.client.post(path, json=payload)
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt + 1 >= max_attempts:
                        raise
                    time.sleep(_retry_delay(None, attempt))
                    continue

                if response.status_code == 429:
                    retry_after = _retry_after_seconds(response)
                    if (
                        attempt < _MAX_RATE_LIMIT_RETRIES
                        and retry_after is not None
                        and retry_after <= _SHORT_RATE_LIMIT_RETRY
                    ):
                        time.sleep(_retry_delay(response, attempt))
                        continue
                    return response

                if (
                    response.status_code not in _RETRYABLE_STATUS_CODES
                    or attempt + 1 >= max_attempts
                ):
                    return response

                time.sleep(_retry_delay(response, attempt))

            return response

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        start = time.perf_counter()

        messages = kwargs.get("messages") or [{"role": "user", "content": prompt}]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 1800),
        }

        if kwargs.get("json_mode", False) and self.supports_json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = self._post("/chat/completions", payload)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"].get("content", "")
        usage = data.get("usage")

        if not content or not content.strip():
            raise ValueError("Empty response from " + self.provider_name)

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider_name,
            usage=usage,
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    def generate_structured(self, prompt: str, response_model: type[T], **kwargs) -> T:
        json_prompt = (
            prompt + "\n\nIMPORTANT: Return ONLY one valid JSON object. "
            "No markdown, no ``` fences, no explanation."
        )

        kwargs.setdefault("max_tokens", 2200)
        kwargs.setdefault("temperature", 0.1)
        kwargs.setdefault("json_mode", True)

        last_error = None
        for attempt in range(2):
            response = self.generate(json_prompt, **kwargs)
            parsed = safe_json_parse(response.content)

            if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
                parsed = parsed[0]

            if not isinstance(parsed, dict):
                parsed = extract_json_from_text(response.content)

            if not isinstance(parsed, dict):
                last_error = ValueError(
                    f"LLM returned invalid JSON (attempt {attempt + 1}). Raw: {response.content[:500]}"
                )
                if attempt == 0:
                    json_prompt = (
                        "Return ONLY a valid JSON object matching this exact structure. "
                        "No text before or after. No markdown.\n\n" + json_prompt
                    )
                continue

            try:
                return response_model.model_validate(parsed)
            except ValidationError as exc:
                last_error = ValueError(f"Validation failed: {exc}")
                if attempt == 0:
                    json_prompt = (
                        "Return ONLY a valid JSON object. All fields required. "
                        "No optional fields. No explanations.\n\n" + json_prompt
                    )
                continue

        raise last_error or ValueError("Failed to generate structured response after retries")

    def get_provider_name(self) -> str:
        return self.provider_name

    def get_model_name(self) -> str:
        return self.model


class GeminiProvider(_HTTPProvider):
    provider_name = "gemini"

    def __init__(self, api_key=None, model=None, base_url=None):
        super().__init__(
            api_key or settings.gemini_api_key,
            model or os.getenv("GEMINI_MODEL", settings.gemini_model),
            base_url or os.getenv("GEMINI_BASE_URL", settings.gemini_base_url),
        )


class GroqProvider(_HTTPProvider):
    provider_name = "groq"
    supports_json_mode = False

    def __init__(self, api_key=None, model=None, base_url=None):
        super().__init__(
            api_key or settings.groq_api_key,
            model or os.getenv("GROQ_MODEL", settings.groq_model),
            base_url or os.getenv("GROQ_BASE_URL", settings.groq_base_url),
        )


class MistralProvider(_HTTPProvider):
    provider_name = "mistral"

    def __init__(self, api_key=None, model=None, base_url=None):
        super().__init__(
            api_key or settings.mistral_api_key,
            model or os.getenv("MISTRAL_MODEL", settings.mistral_model),
            base_url or os.getenv("MISTRAL_BASE_URL", settings.mistral_base_url),
        )


_PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
}


def _build_provider_chain(provider_name: str) -> list:
    priority_str = os.getenv("PROVIDER_PRIORITY", settings.provider_priority)
    priority = [p.strip().lower() for p in priority_str.split(",") if p.strip()]

    if provider_name == "auto":
        ordered = [p for p in priority if p in _PROVIDER_CLASSES]
    elif provider_name in _PROVIDER_CLASSES:
        others = [p for p in priority if p != provider_name and p in _PROVIDER_CLASSES]
        ordered = [provider_name] + others
    else:
        ordered = []

    providers = []
    for name in ordered:
        cls = _PROVIDER_CLASSES[name]
        try:
            providers.append(cls())
        except ValueError:
            continue

    return providers


_RATE_LIMIT_COOLDOWN = _DEFAULT_RATE_LIMIT_COOLDOWN
_MIN_REQUEST_INTERVAL = 5.0
_rate_limit_info: dict[tuple[str, str], float] = {}
_last_request_time: float = 0.0


def _rate_limit_cooldown(exc: BaseException) -> float:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        retry_after = _retry_after_seconds(exc.response)
        if retry_after is not None:
            return min(
                retry_after + _RATE_LIMIT_BUFFER,
                _MAX_RETRY_AFTER,
            )
    return float(_DEFAULT_RATE_LIMIT_COOLDOWN)


class LLMService:
    def __init__(self):
        provider = os.getenv("LLM_PROVIDER", settings.llm_provider).lower()
        self.providers = _build_provider_chain(provider)
        if not self.providers:
            available = ", ".join(_PROVIDER_CLASSES.keys())
            raise ValueError(
                f"No LLM providers configured. Set API keys and models for: {available}"
            )

    @property
    def provider_name(self) -> str:
        return self.providers[0].provider_name

    @property
    def model_name(self) -> str:
        return self.providers[0].get_model_name()

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        last_exc: BaseException | None = None
        errors = []
        for provider in self.providers:
            now = time.time()
            name = provider.get_provider_name()
            key = (name, provider.get_model_name())
            with _rate_limit_lock:
                cooled_until = _rate_limit_info.get(key, 0)
            if now < cooled_until:
                remaining = int(cooled_until - now)
                errors.append(name + f": rate limited (skip for {remaining}s)")
                last_exc = RuntimeError(f"{name} rate limited")
                continue
            try:
                with _request_lock:
                    now = time.time()
                    with _rate_limit_lock:
                        cooled_until = _rate_limit_info.get(key, 0)
                    if now < cooled_until:
                        remaining = int(cooled_until - now)
                        errors.append(name + f": rate limited (skip for {remaining}s)")
                        last_exc = RuntimeError(f"{name} rate limited")
                        continue

                    response = provider.generate(prompt, **kwargs)
                if response.content and response.content.strip():
                    return response
                errors.append(name + ": empty response")
                last_exc = ValueError("Empty response from " + name)
                continue
            except Exception as exc:
                last_exc = exc
                msg = _error_message(exc)
                if is_rate_limit_error(exc):
                    with _rate_limit_lock:
                        _rate_limit_info[key] = time.time() + _rate_limit_cooldown(exc)
                errors.append(name + ": " + msg)
                continue
        error_details = "; ".join(errors) if errors else str(last_exc)
        raise RuntimeError(f"All providers failed. {error_details}") from last_exc

    def generate_structured(self, prompt: str, response_model: type[T], **kwargs) -> T:
        last_exc: BaseException | None = None
        errors = []
        for provider in self.providers:
            now = time.time()
            name = provider.get_provider_name()
            key = (name, provider.get_model_name())
            with _rate_limit_lock:
                cooled_until = _rate_limit_info.get(key, 0)
            if now < cooled_until:
                remaining = int(cooled_until - now)
                errors.append(name + f": rate limited (skip for {remaining}s)")
                last_exc = RuntimeError(f"{name} rate limited")
                continue
            try:
                with _request_lock:
                    now = time.time()
                    with _rate_limit_lock:
                        cooled_until = _rate_limit_info.get(key, 0)
                    if now < cooled_until:
                        remaining = int(cooled_until - now)
                        errors.append(name + f": rate limited (skip for {remaining}s)")
                        last_exc = RuntimeError(f"{name} rate limited")
                        continue

                    response = provider.generate_structured(prompt, response_model, **kwargs)
                return response
            except Exception as exc:
                last_exc = exc
                msg = _error_message(exc)
                if is_rate_limit_error(exc):
                    with _rate_limit_lock:
                        _rate_limit_info[key] = time.time() + _rate_limit_cooldown(exc)
                errors.append(name + ": " + msg)
                continue
        error_details = "; ".join(errors) if errors else str(last_exc)
        raise RuntimeError(f"All providers failed. {error_details}") from last_exc

    def get_provider_name(self) -> str:
        return self.provider_name

    def get_model_name(self) -> str:
        return self.model_name


_llm_service = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def reset_llm_service():
    global _llm_service
    _llm_service = None


def check_provider_health() -> dict:
    import httpx

    results = {}
    test_prompts = {
        "gemini": settings.gemini_api_key,
        "groq": settings.groq_api_key,
        "mistral": settings.mistral_api_key,
    }
    test_models = {
        "gemini": settings.gemini_model,
        "groq": settings.groq_model,
        "mistral": settings.mistral_model,
    }
    test_urls = {
        "gemini": settings.gemini_base_url,
        "groq": settings.groq_base_url,
        "mistral": settings.mistral_base_url,
    }

    for name in ["gemini", "groq", "mistral"]:
        api_key = test_prompts[name]
        model = test_models[name]
        base_url = test_urls[name]

        if not api_key:
            results[name] = {"healthy": False, "error": "No API key configured", "model": model}
            continue

        try:
            timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
            client = httpx.Client(
                base_url=base_url.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            )
            response = client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5,
                },
            )
            client.close()
            if response.status_code == 200:
                results[name] = {"healthy": True, "error": None, "model": model}
            else:
                results[name] = {
                    "healthy": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "model": model,
                }
        except Exception as exc:
            results[name] = {"healthy": False, "error": str(exc), "model": model}

    return results
