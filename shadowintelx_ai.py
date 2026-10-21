"""Optional, user-triggered OpenAI Responses API helper.

Offline coaching is handled elsewhere. This module never contacts a model unless
both OPENAI_API_KEY and OPENAI_MODEL are present and the user requests feedback.
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIConfigurationError(RuntimeError):
    pass


class AIRequestError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip() and os.environ.get("OPENAI_MODEL", "").strip())


def configured_model() -> str | None:
    value = os.environ.get("OPENAI_MODEL", "").strip()
    return value or None


def generate_feedback(instructions: str, input_text: str, timeout_seconds: int = 20) -> str:
    """Call the official Responses API only when a key and model are configured."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    if not api_key or not model:
        raise AIConfigurationError("Model feedback is offline. Configure OPENAI_API_KEY and OPENAI_MODEL to enable it.")
    payload = json.dumps(
        {"model": model, "instructions": instructions, "input": input_text, "store": False},
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=max(3, min(45, int(timeout_seconds)))) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise AIRequestError(f"The configured model service returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AIRequestError("Could not reach the configured model service. Offline coaching remains available.") from None
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    parts = []
    for item in body.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text" and content.get("text"):
                parts.append(str(content["text"]))
    result = "\n".join(parts).strip()
    if not result:
        raise AIRequestError("The configured model returned no text feedback.")
    return result
