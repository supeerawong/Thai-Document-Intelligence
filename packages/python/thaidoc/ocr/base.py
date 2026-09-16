from __future__ import annotations

from typing import Protocol

from PIL import Image


class OCRProvider(Protocol):
    name: str

    def recognize(self, image: Image.Image, *, language: str = "tha+eng") -> str: ...
