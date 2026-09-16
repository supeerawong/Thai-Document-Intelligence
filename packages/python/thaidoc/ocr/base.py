from __future__ import annotations

from typing import Protocol, runtime_checkable

from PIL import Image


@runtime_checkable
class OCRProvider(Protocol):
    name: str

    def recognize(self, image: Image.Image, *, language: str = "tha+eng") -> str: ...
