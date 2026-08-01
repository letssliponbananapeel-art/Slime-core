from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class PdfIngestError(RuntimeError):
    pass


@dataclass(frozen=True)
class PdfInput:
    path: Path
    original_name: str
    sha256: str
    byte_size: int
    page_count: int

    def manifest_entry(self) -> dict[str, object]:
        return {
            "filename": self.original_name,
            "path": str(self.path),
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "page_count": self.page_count,
        }


def safe_filename(name: str, fallback: str) -> str:
    candidate = Path(name).name.strip() or fallback
    return re.sub(r"[^0-9A-Za-z._\-\u3040-\u30ff\u3400-\u9fff]", "_", candidate)


def _page_count(path: Path) -> int:
    try:
        result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, timeout=30, check=False)
    except FileNotFoundError as exc:
        raise PdfIngestError("PDFの情報確認に必要な pdfinfo が見つかりません。") from exc
    except subprocess.TimeoutExpired as exc:
        raise PdfIngestError("PDFの情報確認がタイムアウトしました。") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise PdfIngestError(f"PDFを確認できません。破損または保護されている可能性があります。{detail}")
    match = re.search(r"^Pages:\s*(\d+)", result.stdout, re.MULTILINE)
    if not match or int(match.group(1)) < 1:
        raise PdfIngestError("PDFのページ数を取得できませんでした。")
    return int(match.group(1))


def save_uploaded_pdf(filename: str, content: bytes, destination_dir: Path, max_bytes: int) -> PdfInput:
    if not filename.lower().endswith(".pdf"):
        raise PdfIngestError("PDFファイルを選択してください。")
    if not content:
        raise PdfIngestError("空のPDFは処理できません。")
    if len(content) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise PdfIngestError(f"PDFが大きすぎます。{limit_mb} MB以下のファイルを選択してください。")
    if not content.startswith(b"%PDF-"):
        raise PdfIngestError("PDFとして読み取れません。ファイル形式を確認してください。")

    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = destination_dir / safe_filename(filename, "source.pdf")
    output_path.write_bytes(content)
    return PdfInput(
        path=output_path,
        original_name=filename,
        sha256=hashlib.sha256(content).hexdigest(),
        byte_size=len(content),
        page_count=_page_count(output_path),
    )
