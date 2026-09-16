from __future__ import annotations

import json
from pathlib import Path

import typer

from thaidoc import extract
from thaidoc.benchmark import load_benchmark_manifest, run_ocr_benchmark
from thaidoc.ocr import ImagePreprocessingOptions, create_ocr_provider
from thaidoc.schemas import ThaiOfficialLetter

app = typer.Typer(help="Extract structured data from Thai documents.", no_args_is_help=True)


@app.command("extract")
def extract_command(
    source: Path = typer.Argument(..., exists=True, readable=True),
    schema: str = typer.Option("thai_official_letter", help="Extraction schema name."),
    mode: str = typer.Option("auto", help="rules, ai, or auto."),
    ocr_provider: str = typer.Option("tesseract", "--ocr-provider", help="tesseract or paddle."),
    preprocess: bool = typer.Option(True, "--preprocess/--no-preprocess", help="Preprocess images before OCR."),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    if schema != "thai_official_letter":
        raise typer.BadParameter("Only thai_official_letter is currently available")
    try:
        ocr = create_ocr_provider(ocr_provider)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--ocr-provider") from exc
    result = extract(
        source,
        schema=ThaiOfficialLetter,
        mode=mode,
        ocr=ocr,
        preprocessing=ImagePreprocessingOptions(enabled=preprocess),
    )
    payload = json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)
    if output:
        output.write_text(payload + "\n", encoding="utf-8")
        typer.echo(str(output))
    else:
        typer.echo(payload)


@app.command("benchmark")
def benchmark_command(
    manifest: Path = typer.Argument(..., exists=True, readable=True),
    ocr_provider: str = typer.Option("tesseract", "--ocr-provider", help="tesseract or paddle."),
    output: Path = typer.Option(Path("ocr-benchmark.md"), "--output", "-o"),
    json_output: Path | None = typer.Option(None, "--json-output"),
    preprocess: bool = typer.Option(True, "--preprocess/--no-preprocess"),
) -> None:
    """Evaluate OCR against a local JSONL manifest and write a reproducible report."""
    try:
        provider = create_ocr_provider(ocr_provider)
        cases = load_benchmark_manifest(manifest)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    report = run_ocr_benchmark(
        cases,
        provider,
        preprocessing=ImagePreprocessingOptions(enabled=preprocess),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.to_markdown(), encoding="utf-8")
    if json_output:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    typer.echo(str(output))


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise typer.BadParameter("Install API dependencies with: pip install 'thaidoc[api]'") from exc
    uvicorn.run("thaidoc_api.main:app", host=host, port=port)


if __name__ == "__main__":
    app()
