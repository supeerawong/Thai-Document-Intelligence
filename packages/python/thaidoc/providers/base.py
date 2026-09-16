from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pydantic import BaseModel


class StructuredExtractionProvider(Protocol):
    name: str

    def extract(self, text: str, schema: type[BaseModel]) -> dict[str, Any]: ...
