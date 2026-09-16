from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from thaidoc.loaders import load_document
from thaidoc.normalize import normalize_thai_text
from thaidoc.ocr import ImagePreprocessingOptions, OCRProvider


def _edit_distance(reference: list[str], prediction: list[str]) -> int:
    previous = list(range(len(prediction) + 1))
    for reference_index, reference_item in enumerate(reference, start=1):
        current = [reference_index]
        for prediction_index, prediction_item in enumerate(prediction, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[prediction_index] + 1,
                    previous[prediction_index - 1] + (reference_item != prediction_item),
                )
            )
        previous = current
    return previous[-1]


def character_error_rate(reference: str, prediction: str) -> float:
    expected = list(re.sub(r"\s+", "", normalize_thai_text(reference)))
    actual = list(re.sub(r"\s+", "", normalize_thai_text(prediction)))
    if not expected:
        return 0.0 if not actual else 1.0
    return _edit_distance(expected, actual) / len(expected)


def word_error_rate(reference: str, prediction: str) -> float:
    expected = normalize_thai_text(reference).split()
    actual = normalize_thai_text(prediction).split()
    if not expected:
        return 0.0 if not actual else 1.0
    return _edit_distance(expected, actual) / len(expected)


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    source: Path
    reference: str


@dataclass(frozen=True, slots=True)
class BenchmarkCaseResult:
    case_id: str
    source: str
    character_error_rate: float
    word_error_rate: float
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    provider: str
    cases: list[BenchmarkCaseResult]

    @property
    def mean_character_error_rate(self) -> float:
        return sum(case.character_error_rate for case in self.cases) / len(self.cases) if self.cases else 0.0

    @property
    def mean_word_error_rate(self) -> float:
        return sum(case.word_error_rate for case in self.cases) / len(self.cases) if self.cases else 0.0

    @property
    def total_duration_seconds(self) -> float:
        return sum(case.duration_seconds for case in self.cases)

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "case_count": len(self.cases),
            "mean_character_error_rate": self.mean_character_error_rate,
            "mean_word_error_rate": self.mean_word_error_rate,
            "total_duration_seconds": self.total_duration_seconds,
            "cases": [asdict(case) for case in self.cases],
        }

    def to_markdown(self) -> str:
        rows = [
            "# OCR Benchmark Report",
            "",
            f"- Provider: `{self.provider}`",
            f"- Cases: {len(self.cases)}",
            f"- Mean CER: {self.mean_character_error_rate:.4f}",
            f"- Mean WER: {self.mean_word_error_rate:.4f}",
            f"- Total duration: {self.total_duration_seconds:.3f}s",
            "",
            "| Case | Source | CER | WER | Seconds |",
            "|---|---|---:|---:|---:|",
        ]
        rows.extend(
            f"| {case.case_id} | `{case.source}` | {case.character_error_rate:.4f} | "
            f"{case.word_error_rate:.4f} | {case.duration_seconds:.3f} |"
            for case in self.cases
        )
        return "\n".join(rows) + "\n"


def load_benchmark_manifest(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            item = json.loads(line)
            source = (path.parent / item["source"]).resolve()
            reference = str(item["reference"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"Invalid benchmark manifest line {line_number}") from exc
        if not source.is_file():
            raise ValueError(f"Benchmark source does not exist: {source}")
        cases.append(BenchmarkCase(str(item.get("id", source.stem)), source, reference))
    if not cases:
        raise ValueError("Benchmark manifest contains no cases")
    return cases


def run_ocr_benchmark(
    cases: list[BenchmarkCase],
    provider: OCRProvider,
    *,
    preprocessing: ImagePreprocessingOptions | None = None,
) -> BenchmarkReport:
    results: list[BenchmarkCaseResult] = []
    for case in cases:
        started = time.perf_counter()
        document = load_document(case.source, ocr=provider, preprocessing=preprocessing)
        prediction = "\n".join(page.text for page in document.pages)
        results.append(
            BenchmarkCaseResult(
                case_id=case.case_id,
                source=str(case.source),
                character_error_rate=character_error_rate(case.reference, prediction),
                word_error_rate=word_error_rate(case.reference, prediction),
                duration_seconds=time.perf_counter() - started,
            )
        )
    return BenchmarkReport(provider=provider.name, cases=results)
