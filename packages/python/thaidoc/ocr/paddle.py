from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from PIL import Image


def _find_recognized_text(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        texts = value.get("rec_texts")
        if isinstance(texts, Iterable) and not isinstance(texts, (str, bytes)):
            return [str(item).strip() for item in texts if str(item).strip()]
        for child in value.values():
            found = _find_recognized_text(child)
            if found:
                return found
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        # PaddleOCR 2.x returned [box, (text, confidence)] entries.
        items = list(value)
        legacy: list[str] = []
        for item in items:
            if (
                isinstance(item, (list, tuple))
                and len(item) == 2
                and isinstance(item[1], (list, tuple))
                and item[1]
                and isinstance(item[1][0], str)
            ):
                legacy.append(item[1][0].strip())
        if legacy:
            return [item for item in legacy if item]
        for child in items:
            found = _find_recognized_text(child)
            if found:
                return found
    return []


class PaddleOCRProvider:
    """Local PaddleOCR 3.x provider loaded lazily to keep the core lightweight."""

    name = "paddle"

    def __init__(self, model: Any | None = None) -> None:
        self._model = model

    def _get_model(self, language: str) -> Any:
        if self._model is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as exc:
                raise RuntimeError(
                    "PaddleOCR is not installed. Install it with: pip install 'thaidoc[paddle]'"
                ) from exc
            paddle_language = "th" if "tha" in language or "th" in language else "en"
            self._model = PaddleOCR(
                lang=paddle_language,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=True,
            )
        return self._model

    def recognize(self, image: Image.Image, *, language: str = "tha+eng") -> str:
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("PaddleOCR requires numpy; install 'thaidoc[paddle]'") from exc

        model = self._get_model(language)
        if hasattr(model, "predict"):
            results = model.predict(np.asarray(image.convert("RGB")))
        else:  # Compatibility with PaddleOCR 2.x model objects supplied by callers.
            results = model.ocr(np.asarray(image.convert("RGB")), cls=True)

        lines: list[str] = []
        for result in results:
            payload = getattr(result, "json", result)
            if callable(payload):
                payload = payload()
            lines.extend(_find_recognized_text(payload))
        return "\n".join(dict.fromkeys(lines))
