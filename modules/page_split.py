from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class PageSplitError(RuntimeError):
    pass


def split_pdf_pages(pdf_path: Path, output_dir: Path, dpi: int, timeout_seconds: int) -> list[Path]:
    if not pdf_path.exists():
        raise PageSplitError("ページ画像の準備に失敗しました。PDFが見つかりません。")
    if shutil.which("pdftoppm") is None:
        raise PageSplitError("ページ画像の準備に必要な pdftoppm が見つかりません。")

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "page"
    try:
        result = subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PageSplitError("ページ画像の準備がタイムアウトしました。ページ数を減らして再実行してください。") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise PageSplitError(f"ページ画像の準備に失敗しました。{detail}")

    pages = sorted(output_dir.glob("page-*.png"))
    if not pages:
        raise PageSplitError("ページ画像の準備に失敗しました。PNGを生成できませんでした。")
    return pages
