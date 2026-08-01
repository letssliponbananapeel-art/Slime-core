from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from queue import Empty, Queue
from pathlib import Path
from typing import Any

import streamlit as st

from .config import PipelineConfig, load_config
from .ocr_runner import OcrRunnerError, is_ndlocr_available
from .page_split import PageSplitError
from .pdf_ingest import PdfIngestError
from .pipeline import PipelineResult, process_ocr_json_upload, process_pdf_upload
from .translator import TranslationError


UI_TEXT = {
    "ja": {
        "title": "古文処理",
        "subtitle": "PDFまたはOCR JSONを、根拠を残しながら現代語訳へ変換します。",
        "upload": "PDF または OCR JSON",
        "model": "現代語訳モデル",
        "start": "現代語訳を開始",
        "running": "古文処理を実行中です。会話タブはそのまま使えます。",
        "done": "古文処理が完了しました。",
        "result": "現代語訳",
        "download_translation": "translation.txt をダウンロード",
        "download_manifest": "manifest.json をダウンロード",
        "files": "保存された成果物",
        "missing_binary": "NDLOCR-Lite が見つかりません。PDF処理には導入が必要です。OCR JSONは検証できます。",
        "pdf_blocked": "NDLOCR-Liteを導入してからPDF処理を開始できます。OCR JSONはそのまま検証できます。",
        "binary_ready": "NDLOCR-Lite を検出しました。PDFを全ページ処理できます。",
        "settings": "処理設定",
        "error": "古文処理を完了できませんでした。",
        "refresh": "処理状況は自動更新されます。",
        "fixture_hint": "既存のOCR JSONを選ぶと、NDLOCR-Lite未導入でもフィルタと訳文処理を確認できます。",
    },
    "en": {
        "title": "Classical Text",
        "subtitle": "Turn a PDF or OCR JSON into a modern Japanese translation while preserving evidence.",
        "upload": "PDF or OCR JSON",
        "model": "Translation model",
        "start": "Start Translation",
        "running": "Classical-text processing is running. The chat tab remains available.",
        "done": "Classical-text processing is complete.",
        "result": "Modern Japanese Translation",
        "download_translation": "Download translation.txt",
        "download_manifest": "Download manifest.json",
        "files": "Saved artifacts",
        "missing_binary": "NDLOCR-Lite was not found. Install it to process PDFs. OCR JSON can still be verified.",
        "pdf_blocked": "Install NDLOCR-Lite before starting PDF processing. OCR JSON can still be verified.",
        "binary_ready": "NDLOCR-Lite is available. PDFs will be processed page by page.",
        "settings": "Processing settings",
        "error": "Classical-text processing could not be completed.",
        "refresh": "Processing status refreshes automatically.",
        "fixture_hint": "Choose an existing OCR JSON to verify filtering and translation without NDLOCR-Lite.",
    },
}


def _text(language: str) -> dict[str, str]:
    return UI_TEXT.get(language, UI_TEXT["ja"])


def can_start_processing(upload_name: str | None, ocr_available: bool, job_active: bool) -> bool:
    """Allow OCR JSON without NDLOCR-Lite, but require it for PDF input."""
    if not upload_name or job_active:
        return False
    return not upload_name.lower().endswith(".pdf") or ocr_available


def _init_state() -> None:
    if "kobun_executor" not in st.session_state:
        st.session_state.kobun_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="slimecore-kobun")
    defaults: dict[str, Any] = {
        "kobun_job": None,
        "kobun_result": None,
        "kobun_error": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _error_message(error: Exception) -> str:
    if isinstance(error, OcrRunnerError):
        return error.user_message
    if isinstance(error, (PdfIngestError, PageSplitError, TranslationError, ValueError)):
        return str(error)
    return f"予期しないエラーが発生しました: {error}"


def _start_job(uploaded_name: str, content: bytes, config: PipelineConfig, model: str) -> None:
    progress: Queue[str] = Queue()

    def run() -> PipelineResult:
        if uploaded_name.lower().endswith(".pdf"):
            return process_pdf_upload(uploaded_name, content, config, model, progress=progress.put)
        return process_ocr_json_upload(uploaded_name, content, config, model, progress=progress.put)

    executor: ThreadPoolExecutor = st.session_state.kobun_executor
    future: Future[PipelineResult] = executor.submit(run)
    st.session_state.kobun_job = {"future": future, "progress": progress, "messages": []}
    st.session_state.kobun_result = None
    st.session_state.kobun_error = ""


def _render_running_job(copy: dict[str, str]) -> None:
    job = st.session_state.get("kobun_job")
    if not job:
        return

    @st.fragment(run_every=1)
    def poll() -> None:
        active_job = st.session_state.get("kobun_job")
        if not active_job:
            return
        progress: Queue[str] = active_job["progress"]
        messages: list[str] = active_job["messages"]
        while True:
            try:
                messages.append(progress.get_nowait())
            except Empty:
                break
        future: Future[PipelineResult] = active_job["future"]
        if future.done():
            try:
                st.session_state.kobun_result = future.result()
                st.session_state.kobun_error = ""
            except Exception as exc:
                st.session_state.kobun_error = _error_message(exc)
            st.session_state.kobun_job = None
            st.rerun()
        else:
            label = messages[-1] if messages else copy["running"]
            st.info(label)
            st.caption(copy["refresh"])

    poll()


def _render_result(copy: dict[str, str]) -> None:
    result: PipelineResult | None = st.session_state.get("kobun_result")
    if not result:
        return
    if not result.translation_path.exists() or not result.manifest_path.exists():
        st.session_state.kobun_result = None
        return
    st.success(copy["done"])
    st.markdown(f"#### {copy['result']}")
    st.text_area(
        "kobun_translation_result",
        value=result.translation,
        height=300,
        label_visibility="collapsed",
        disabled=True,
    )
    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            copy["download_translation"],
            data=result.translation_path.read_bytes(),
            file_name="translation.txt",
            mime="text/plain",
            width="stretch",
        )
    with c2:
        st.download_button(
            copy["download_manifest"],
            data=result.manifest_path.read_bytes(),
            file_name="manifest.json",
            mime="application/json",
            width="stretch",
        )
    with st.expander(copy["files"]):
        st.code(str(result.session_dir), language=None)
        for path in sorted(result.session_dir.rglob("*")):
            if path.is_file():
                st.caption(str(path.relative_to(result.session_dir)))


def render_kobun_panel(app_dir: str, default_model: str, ui_language: str) -> None:
    _init_state()
    copy = _text(ui_language)
    try:
        config = load_config(Path(app_dir))
    except ValueError as exc:
        st.error(str(exc))
        return

    st.markdown(f"<div class='main-title'>{copy['title']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='main-subtitle'>{copy['subtitle']}</div>", unsafe_allow_html=True)
    available = is_ndlocr_available(config.ocr_binary)
    if available:
        st.success(copy["binary_ready"])
    else:
        st.warning(copy["missing_binary"])

    with st.expander(copy["settings"]):
        st.json(
            {
                "ocr_binary": config.ocr_binary,
                "ocr_timeout_seconds": config.ocr_timeout_seconds,
                "pdf_dpi": config.pdf_dpi,
                "confidence_threshold": config.confidence_threshold,
                "jp_char_ratio_threshold": config.jp_char_ratio_threshold,
                "output_directory": str(config.output_dir),
            }
        )

    uploaded = st.file_uploader(copy["upload"], type=["pdf", "json"], key="kobun_input")
    model = st.text_input(copy["model"], value=default_model, key="kobun_model")
    if uploaded and uploaded.name.lower().endswith(".json"):
        st.caption(copy["fixture_hint"])
    if uploaded and uploaded.name.lower().endswith(".pdf") and not available:
        st.info(copy["pdf_blocked"])

    existing_job = st.session_state.get("kobun_job")
    can_start = can_start_processing(
        uploaded.name if uploaded else None,
        ocr_available=available,
        job_active=bool(existing_job),
    )
    start = st.button(copy["start"], type="primary", width="stretch", disabled=not can_start)
    if start and uploaded:
        _start_job(uploaded.name, uploaded.getvalue(), config, model.strip() or default_model)
        st.rerun()

    _render_running_job(copy)
    if st.session_state.get("kobun_error"):
        st.error(f"{copy['error']} {st.session_state.kobun_error}")
    _render_result(copy)
