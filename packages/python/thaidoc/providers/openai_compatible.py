from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


class OpenAICompatibleProvider:
    """Structured extraction through an OpenAI-compatible chat-completions API."""

    name = "openai-compatible"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def extract(self, text: str, schema: type[BaseModel]) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("Install AI support with: pip install 'thaidoc[ai]'") from exc
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            timeout=self.timeout,
            json={
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "Extract only values supported by the document. Use null for missing values.",
                    },
                    {"role": "user", "content": text},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "strict": True, "schema": schema.model_json_schema()},
                },
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return schema.model_validate(data).model_dump(mode="json")
