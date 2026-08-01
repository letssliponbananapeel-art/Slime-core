from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "ocr": {
        "binary": "tools/ndlocr-lite-run",
        "args": ["--sourceimg", "{input}", "--output", "{output}", "--json-only"],
        "timeout_seconds": 300,
    },
    "pdf": {
        "dpi": 180,
        "split_timeout_seconds": 300,
        "max_upload_megabytes": 200,
    },
    "filter": {
        "confidence_threshold": 0.5,
        "jp_char_ratio_threshold": 0.5,
        "missing_confidence_policy": "unclear",
    },
    "ollama": {
        "host": "http://127.0.0.1:11434",
        "timeout_seconds": 300,
        "num_predict": 900,
        "temperature": 0.15,
    },
    "output": {"directory": "outputs"},
}


@dataclass(frozen=True)
class PipelineConfig:
    app_dir: Path
    ocr_binary: str
    ocr_args: tuple[str, ...]
    ocr_timeout_seconds: int
    pdf_dpi: int
    pdf_split_timeout_seconds: int
    max_upload_bytes: int
    confidence_threshold: float
    jp_char_ratio_threshold: float
    missing_confidence_policy: str
    ollama_host: str
    ollama_timeout_seconds: int
    ollama_num_predict: int
    ollama_temperature: float
    output_dir: Path

    def manifest_settings(self) -> dict[str, Any]:
        return {
            "ocr": {
                "binary": self.ocr_binary,
                "args": list(self.ocr_args),
                "timeout_seconds": self.ocr_timeout_seconds,
            },
            "pdf": {
                "dpi": self.pdf_dpi,
                "split_timeout_seconds": self.pdf_split_timeout_seconds,
                "max_upload_bytes": self.max_upload_bytes,
            },
            "filter": {
                "confidence_threshold": self.confidence_threshold,
                "jp_char_ratio_threshold": self.jp_char_ratio_threshold,
                "missing_confidence_policy": self.missing_confidence_policy,
            },
            "ollama": {
                "host": self.ollama_host,
                "timeout_seconds": self.ollama_timeout_seconds,
                "num_predict": self.ollama_num_predict,
                "temperature": self.ollama_temperature,
            },
        }


def _merge_defaults(defaults: dict[str, Any], supplied: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key, default_value in defaults.items():
        supplied_value = supplied.get(key)
        if isinstance(default_value, dict) and isinstance(supplied_value, dict):
            merged[key] = _merge_defaults(default_value, supplied_value)
        elif supplied_value is None:
            merged[key] = default_value
        else:
            merged[key] = supplied_value
    return merged


def load_config(app_dir: Path, config_path: Path | None = None) -> PipelineConfig:
    path = config_path or app_dir / "app_config.json"
    supplied: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"設定ファイルのJSON形式が正しくありません: {path}") from exc
        if not isinstance(loaded, dict):
            raise ValueError(f"設定ファイルはJSONオブジェクトである必要があります: {path}")
        supplied = loaded

    data = _merge_defaults(DEFAULT_CONFIG, supplied)
    ocr = data["ocr"]
    pdf = data["pdf"]
    filtering = data["filter"]
    ollama = data["ollama"]
    output = data["output"]
    output_dir = Path(str(output["directory"]))
    if not output_dir.is_absolute():
        output_dir = app_dir / output_dir

    args = ocr["args"]
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise ValueError("ocr.args は文字列の配列である必要があります")

    binary = str(ocr["binary"])
    binary_path = Path(binary).expanduser()
    if not binary_path.is_absolute() and "/" in binary:
        binary = str(app_dir / binary_path)

    return PipelineConfig(
        app_dir=app_dir,
        ocr_binary=binary,
        ocr_args=tuple(args),
        ocr_timeout_seconds=max(1, int(ocr["timeout_seconds"])),
        pdf_dpi=max(72, int(pdf["dpi"])),
        pdf_split_timeout_seconds=max(1, int(pdf["split_timeout_seconds"])),
        max_upload_bytes=max(1, int(pdf["max_upload_megabytes"])) * 1024 * 1024,
        confidence_threshold=float(filtering["confidence_threshold"]),
        jp_char_ratio_threshold=float(filtering["jp_char_ratio_threshold"]),
        missing_confidence_policy=str(filtering["missing_confidence_policy"]),
        ollama_host=str(ollama["host"]).rstrip("/"),
        ollama_timeout_seconds=max(1, int(ollama["timeout_seconds"])),
        ollama_num_predict=max(32, int(ollama["num_predict"])),
        ollama_temperature=float(ollama["temperature"]),
        output_dir=output_dir,
    )
