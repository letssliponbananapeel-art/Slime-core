from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .confidence_filter import filter_page
from .config import PipelineConfig
from .exporters import SessionPaths, create_session, write_json, write_manifest, write_translation
from .models import OcrPageResult
from .ocr_runner import OcrRunnerError, run_page_ocr
from .page_split import PageSplitError, split_pdf_pages
from .pdf_ingest import PdfIngestError, save_uploaded_pdf, safe_filename
from .translator import OllamaTranslator, TextGenerator, TranslationError, build_translation


ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class PipelineResult:
    session_id: str
    session_dir: Path
    translation_path: Path
    manifest_path: Path
    translation: str
    warnings: list[str]


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _notify(callback: ProgressCallback | None, message: str) -> None:
    if callback:
        callback(message)


def _generator(config: PipelineConfig, model: str) -> OllamaTranslator:
    return OllamaTranslator(
        host=config.ollama_host,
        model=model,
        timeout_seconds=config.ollama_timeout_seconds,
        num_predict=config.ollama_num_predict,
        temperature=config.ollama_temperature,
    )


def _base_manifest(paths: SessionPaths, config: PipelineConfig, input_kind: str) -> dict[str, object]:
    return {
        "session_id": paths.session_id,
        "state": "running",
        "started_at": _now(),
        "input_kind": input_kind,
        "settings": config.manifest_settings(),
        "input": {},
        "artifacts": {"pages": [], "ocr": [], "filtered": [], "translation": None},
        "warnings": [],
        "errors": [],
    }


def _finish_success(
    paths: SessionPaths,
    manifest: dict[str, object],
    translation: str,
    warnings: list[str],
) -> PipelineResult:
    translation_path = write_translation(paths, translation)
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, dict)
    artifacts["translation"] = str(translation_path.relative_to(paths.root))
    manifest["state"] = "completed"
    manifest["completed_at"] = _now()
    manifest["warnings"] = warnings
    write_manifest(paths, manifest)
    return PipelineResult(
        session_id=paths.session_id,
        session_dir=paths.root,
        translation_path=translation_path,
        manifest_path=paths.manifest_path,
        translation=translation,
        warnings=warnings,
    )


def _finish_failure(paths: SessionPaths, manifest: dict[str, object], error: Exception) -> None:
    manifest["state"] = "failed"
    manifest["completed_at"] = _now()
    manifest["errors"] = [{"type": type(error).__name__, "message": str(error)}]
    write_manifest(paths, manifest)


def _save_page_results(
    paths: SessionPaths,
    page_name: str,
    page: OcrPageResult,
    config: PipelineConfig,
    manifest: dict[str, object],
) -> tuple[list, list[str]]:
    ocr_path = paths.ocr_dir / f"{Path(page_name).stem}.json"
    write_json(ocr_path, page.to_dict())
    filtered = filter_page(
        page,
        confidence_threshold=config.confidence_threshold,
        jp_ratio_threshold=config.jp_char_ratio_threshold,
    )
    filtered_path = paths.filtered_dir / f"{Path(page_name).stem}.json"
    write_json(
        filtered_path,
        {
            "ocr": page.to_dict(),
            "filter": {
                "confidence_threshold": config.confidence_threshold,
                "jp_char_ratio_threshold": config.jp_char_ratio_threshold,
            },
            "results": [line.to_dict() for line in filtered],
        },
    )
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, dict)
    for key, value in (("ocr", ocr_path), ("filtered", filtered_path)):
        stored = artifacts[key]
        assert isinstance(stored, list)
        stored.append(str(value.relative_to(paths.root)))

    warnings: list[str] = []
    if filtered and all(line.confidence_missing for line in filtered):
        warnings.append(f"{page_name}: OCR出力にconfidenceが無いため、全行を不明瞭として扱いました。")
    return filtered, warnings


def process_pdf_upload(
    filename: str,
    content: bytes,
    config: PipelineConfig,
    model: str,
    progress: ProgressCallback | None = None,
    generator: TextGenerator | None = None,
) -> PipelineResult:
    paths = create_session(config.output_dir)
    manifest = _base_manifest(paths, config, "pdf")
    write_manifest(paths, manifest)
    try:
        _notify(progress, "PDFを確認しています")
        source = save_uploaded_pdf(filename, content, paths.source_dir, config.max_upload_bytes)
        manifest["input"] = source.manifest_entry()
        _notify(progress, "PDFをページ画像へ変換しています")
        page_paths = split_pdf_pages(
            source.path,
            output_dir=paths.pages_dir,
            dpi=config.pdf_dpi,
            timeout_seconds=config.pdf_split_timeout_seconds,
        )
        artifacts = manifest["artifacts"]
        assert isinstance(artifacts, dict)
        pages = artifacts["pages"]
        assert isinstance(pages, list)
        pages.extend(str(path.relative_to(paths.root)) for path in page_paths)

        client = generator or _generator(config, model)
        translations: list[str] = []
        warnings: list[str] = []
        for number, page_path in enumerate(page_paths, start=1):
            _notify(progress, f"{number}/{len(page_paths)}ページをOCRしています")
            page = run_page_ocr(
                page_path,
                binary=config.ocr_binary,
                args=config.ocr_args,
                timeout_seconds=config.ocr_timeout_seconds,
            )
            filtered, page_warnings = _save_page_results(paths, page_path.name, page, config, manifest)
            warnings.extend(page_warnings)
            _notify(progress, f"{number}/{len(page_paths)}ページを現代語訳しています")
            translations.append(build_translation(filtered, client))

        _notify(progress, "訳文と処理記録を保存しています")
        return _finish_success(paths, manifest, "\n\n".join(part for part in translations if part), warnings)
    except (PdfIngestError, PageSplitError, OcrRunnerError, TranslationError, OSError, ValueError) as exc:
        _finish_failure(paths, manifest, exc)
        raise


def process_ocr_json_upload(
    filename: str,
    content: bytes,
    config: PipelineConfig,
    model: str,
    progress: ProgressCallback | None = None,
    generator: TextGenerator | None = None,
) -> PipelineResult:
    paths = create_session(config.output_dir)
    manifest = _base_manifest(paths, config, "ocr_json")
    write_manifest(paths, manifest)
    try:
        if not filename.lower().endswith(".json"):
            raise ValueError("OCR JSONファイルを選択してください。")
        if not content:
            raise ValueError("空のOCR JSONは処理できません。")
        source_path = paths.source_dir / safe_filename(filename, "ocr.json")
        source_path.write_bytes(content)
        raw = json.loads(content.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("OCR JSONの最上位はオブジェクトである必要があります。")
        manifest["input"] = {
            "filename": filename,
            "path": str(source_path),
            "sha256": hashlib.sha256(content).hexdigest(),
            "byte_size": len(content),
        }
        _notify(progress, "OCR JSONを正規化して検査しています")
        page = OcrPageResult.from_mapping(raw)
        if not page.contents or not page.contents[0]:
            raise ValueError("OCR JSONに読み取り行がありません。")
        filtered, warnings = _save_page_results(paths, source_path.name, page, config, manifest)
        _notify(progress, "現代語訳を生成しています")
        translation = build_translation(filtered, generator or _generator(config, model))
        _notify(progress, "訳文と処理記録を保存しています")
        return _finish_success(paths, manifest, translation, warnings)
    except (TranslationError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _finish_failure(paths, manifest, exc)
        raise
