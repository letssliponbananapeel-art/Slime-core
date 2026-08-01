from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class SessionPaths:
    session_id: str
    root: Path
    source_dir: Path
    pages_dir: Path
    ocr_dir: Path
    filtered_dir: Path
    translation_dir: Path
    manifest_path: Path


def create_session(output_root: Path) -> SessionPaths:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{timestamp}_{uuid4().hex[:8]}"
    root = output_root / session_id
    paths = SessionPaths(
        session_id=session_id,
        root=root,
        source_dir=root / "source",
        pages_dir=root / "pages",
        ocr_dir=root / "ocr",
        filtered_dir=root / "filtered",
        translation_dir=root / "translation",
        manifest_path=root / "manifest.json",
    )
    for directory in (paths.source_dir, paths.pages_dir, paths.ocr_dir, paths.filtered_dir, paths.translation_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return paths


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_translation(paths: SessionPaths, text: str) -> Path:
    output = paths.translation_dir / "translation.txt"
    output.write_text(text.rstrip() + "\n", encoding="utf-8")
    return output


def write_manifest(paths: SessionPaths, payload: dict[str, object]) -> Path:
    write_json(paths.manifest_path, payload)
    return paths.manifest_path
