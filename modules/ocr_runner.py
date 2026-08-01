from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from .models import OcrLine, OcrPageResult


DEFAULT_CONFIDENCE_FALLBACK = 0.0


class OcrRunnerError(RuntimeError):
    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail

    @property
    def user_message(self) -> str:
        messages = {
            "image_missing": "ページ画像の準備に失敗しました。もう一度PDFを読み込み直してください。",
            "binary_missing": "文字の読み取りに必要なNDLOCR-Liteが見つかりません。導入状態を確認してください。",
            "timeout": "読み取りに時間がかかりすぎています。ページ数を減らすか、しばらく待って再実行してください。",
            "process_failed": "文字の読み取りに失敗しました。NDLOCR-Liteが正しくインストールされているか確認してください。",
            "invalid_json": "読み取り結果の形式が想定と異なります。開発者に報告してください。",
        }
        return messages.get(self.kind, "文字の読み取りに失敗しました。")


def _resolve_binary(binary: str) -> str | None:
    path = Path(binary).expanduser()
    if path.is_absolute() or "/" in binary:
        return str(path) if path.exists() else None
    return shutil.which(binary)


def is_ndlocr_available(binary: str) -> bool:
    return _resolve_binary(binary) is not None


def _build_command(
    binary: str,
    args: tuple[str, ...],
    image_path: Path,
    output_dir: Path | None = None,
) -> list[str]:
    substitutions = {"{input}": str(image_path)}
    if output_dir is not None:
        substitutions["{output}"] = str(output_dir)
    substituted = [
        item.replace("{input}", substitutions["{input}"]).replace("{output}", substitutions.get("{output}", "{output}"))
        for item in args
    ]
    if not any("{input}" in item for item in args):
        substituted.append(str(image_path))
    return [binary, *substituted]


def _read_ocr_payload(stdout: str, output_dir: Path | None, image_path: Path) -> dict[str, Any]:
    if output_dir is None:
        raw = stdout
    else:
        expected = output_dir / f"{image_path.stem}.json"
        candidates = [expected] if expected.exists() else sorted(output_dir.glob("*.json"))
        if len(candidates) != 1:
            raise OcrRunnerError("invalid_json", "NDLOCR-LiteのJSON出力を特定できませんでした。")
        raw = candidates[0].read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OcrRunnerError("invalid_json", f"invalid NDLOCR-Lite output: {exc}") from exc
    if not isinstance(payload, dict):
        raise OcrRunnerError("invalid_json", "NDLOCR-Lite output must be a JSON object")
    return payload


def run_ndlocr_lite(image_path: Path, binary: str, args: tuple[str, ...], timeout_seconds: int) -> dict[str, Any]:
    if not image_path.exists():
        raise OcrRunnerError("image_missing", f"image not found: {image_path}")
    executable = _resolve_binary(binary)
    if executable is None:
        raise OcrRunnerError("binary_missing", f"NDLOCR-Lite binary not found: {binary}")
    uses_output_directory = any("{output}" in item for item in args)
    try:
        with tempfile.TemporaryDirectory(prefix="slimecore-ndlocr-") as directory:
            output_dir = Path(directory) if uses_output_directory else None
            proc = subprocess.run(
                _build_command(executable, args, image_path, output_dir=output_dir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()
                raise OcrRunnerError("process_failed", f"NDLOCR-Lite failed (code={proc.returncode}): {detail}")
            return _read_ocr_payload(proc.stdout, output_dir, image_path)
    except subprocess.TimeoutExpired as exc:
        raise OcrRunnerError("timeout", f"NDLOCR-Lite timed out: {image_path}") from exc


def _raw_lines(raw: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contents = raw.get("contents")
    if isinstance(contents, list) and contents:
        if isinstance(contents[0], list):
            return [item for item in contents[0] if isinstance(item, Mapping)]
        return [item for item in contents if isinstance(item, Mapping)]
    for key in ("lines", "textLines", "annotations"):
        candidate = raw.get(key)
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, Mapping)]
    return []


def normalize_result(raw: Mapping[str, Any], image_path: Path) -> OcrPageResult:
    lines = [OcrLine.from_mapping(item, fallback_id=index) for index, item in enumerate(_raw_lines(raw))]
    try:
        with Image.open(image_path) as image:
            width, height = image.size
    except OSError as exc:
        raise OcrRunnerError("image_missing", f"could not read image: {image_path}") from exc
    return OcrPageResult(
        contents=[lines],
        imginfo={
            "img_width": width,
            "img_height": height,
            "img_path": str(image_path),
            "img_name": image_path.name,
        },
    )


def run_page_ocr(image_path: Path, binary: str, args: tuple[str, ...], timeout_seconds: int) -> OcrPageResult:
    raw = run_ndlocr_lite(image_path, binary=binary, args=args, timeout_seconds=timeout_seconds)
    return normalize_result(raw, image_path)
