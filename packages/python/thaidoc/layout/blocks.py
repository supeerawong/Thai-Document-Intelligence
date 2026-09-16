from pydantic import BaseModel

from thaidoc.models import PageContent


class TextBlock(BaseModel):
    page: int
    line: int
    text: str
    method: str


def reconstruct_blocks(pages: list[PageContent]) -> list[TextBlock]:
    return [
        TextBlock(page=page.page, line=index, text=line, method=page.method)
        for page in pages
        for index, line in enumerate(page.text.splitlines(), start=1)
        if line.strip()
    ]
