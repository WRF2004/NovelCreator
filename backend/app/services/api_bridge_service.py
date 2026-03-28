from __future__ import annotations

import json
from typing import Any

import requests

from app.schemas import APIBridgeConfig


class APIBridgeError(RuntimeError):
    pass


def call_chat_completion(
    config: APIBridgeConfig,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1200,
) -> str:
    if not config.enabled:
        raise APIBridgeError("API bridge not enabled.")
    if not config.base_url or not config.api_key or not config.model:
        raise APIBridgeError("API bridge config incomplete.")

    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": config.model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    if response.status_code >= 400:
        raise APIBridgeError(f"API request failed: {response.status_code} {response.text}")

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise APIBridgeError("API response has no choices.")

    content = choices[0].get("message", {}).get("content")
    if not content:
        raise APIBridgeError("API response has empty content.")

    return str(content).strip()

