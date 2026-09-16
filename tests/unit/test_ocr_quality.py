import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from pytest import MonkeyPatch
from thaidoc.benchmark import (
    BenchmarkCase,
    character_error_rate,
    run_ocr_benchmark,
    word_error_rate,
)
from thaidoc.ocr import ImagePreprocessingOptions
from thaidoc.ocr.paddle import PaddleOCRProvider, _find_recognized_text


class StaticOCR:
    name = "static"

    def recognize(self, image: Image.Image, *, language: str = "tha+eng") -> str:
        return "เรื่อง ทดสอบระบบ"


def test_ocr_error_rates() -> None:
    assert character_error_rate("ภาษาไทย", "ภาษาไท") == 1 / 7
    assert word_error_rate("เรื่อง ทดสอบ ระบบ", "เรื่อง ทดสอบ งาน") == 1 / 3
    assert character_error_rate("", "") == 0


def test_paddle_v3_result_text_is_extracted() -> None:
    payload = {"res": {"rec_texts": ["เรื่อง ทดสอบ", "เรียน ผู้อำนวยการ"]}}
    assert _find_recognized_text(payload) == ["เรื่อง ทดสอบ", "เรียน ผู้อำนวยการ"]


def test_paddle_provider_accepts_v3_result_objects(monkeypatch: MonkeyPatch) -> None:
    class Result:
        json = {"res": {"rec_texts": ["เรื่อง ทดสอบ"]}}

    class Model:
        def predict(self, image: object) -> list[Result]:
            return [Result()]

    # Keep the default development test suite independent from the large optional runtime.
    monkeypatch.setitem(sys.modules, "numpy", SimpleNamespace(asarray=lambda image: image))
    provider = PaddleOCRProvider(model=Model())

    assert provider.recognize(Image.new("RGB", (10, 10))) == "เรื่อง ทดสอบ"


def test_benchmark_report_uses_local_fixture(tmp_path: Path) -> None:
    source = tmp_path / "case.png"
    Image.new("RGB", (100, 100), "white").save(source)
    report = run_ocr_benchmark(
        [BenchmarkCase("case-1", source, "เรื่อง ทดสอบระบบ")],
        StaticOCR(),
        preprocessing=ImagePreprocessingOptions(enabled=False),
    )

    assert report.mean_character_error_rate == 0
    assert report.mean_word_error_rate == 0
    assert "| case-1 |" in report.to_markdown()
