from __future__ import annotations

import json
from pathlib import Path

import typer

from thaidoc import extract
from thaidoc.schemas import ThaiOfficialLetter

app = typer.Typer(help="Extract structured data from Thai documents.", no_args_is_help=True)


@app.command("extract")
def extract_command(
    source: Path = typer.Argument(..., exists=True, readable=True),
    schema: str = typer.Option("thai_official_letter", help="Extraction schema name."),
    mode: str = typer.Option("auto", help="rules, ai, or auto."),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    if schema != "thai_official_letter":
        raise typer.BadParameter("Only thai_official_letter is available in v0.1")
    result = extract(source, schema=ThaiOfficialLetter, mode=mode)
    payload = json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)
    if output:
        output.write_text(payload + "\n", encoding="utf-8")
        typer.echo(str(output))
    else:
        typer.echo(payload)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise typer.BadParameter("Install API dependencies with: pip install 'thaidoc[api]'") from exc
    uvicorn.run("thaidoc_api.main:app", host=host, port=port)


if __name__ == "__main__":
    app()
