from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import requests

from .models import FilterResult, TranslationChunk


UNCLEAR_MARK = "(原文不明瞭)"
SENTENCE_END_CHARS = ("。", "！", "？", "!", "?", "．")


class TranslationError(RuntimeError):
    pass


class TextGenerator(Protocol):
    def generate(self, source_text: str) -> str:
        """Return a modern Japanese translation for one chunk."""


@dataclass
class OllamaTranslator:
    host: str
    model: str
    timeout_seconds: int
    num_predict: int
    temperature: float

    def generate(self, source_text: str) -> str:
        prompt = (
            "次の古文・近代史料のOCR本文を、意味を補い過ぎず自然な現代日本語に訳してください。\n"
            "出力は現代語訳だけにし、見出し、解説、箇条書き、原文の再掲は含めません。\n\n"
            f"原文:\n{source_text}\n\n現代語訳:"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは古文資料の慎重な現代語訳者です。"},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "think": False,
            "options": {"temperature": self.temperature, "num_predict": self.num_predict},
        }
        try:
            response = requests.post(f"{self.host.rstrip('/')}/api/chat", json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise TranslationError("現代語訳の生成がタイムアウトしました。") from exc
        except requests.exceptions.ConnectionError as exc:
            raise TranslationError("Ollamaに接続できません。`ollama serve` を確認してください。") from exc
        except requests.RequestException as exc:
            raise TranslationError(f"現代語訳の生成に失敗しました: {exc}") from exc

        translated = str(((response.json().get("message") or {}).get("content") or "")).strip()
        if not translated:
            raise TranslationError("現代語訳が空でした。モデルを変えて再実行してください。")
        return translated


def build_chunks(filtered_lines: list[FilterResult]) -> list[TranslationChunk | str]:
    sequence: list[TranslationChunk | str] = []
    buffer_ids: list[int] = []
    buffer_text = ""

    def flush() -> None:
        nonlocal buffer_ids, buffer_text
        if buffer_text:
            sequence.append(TranslationChunk(line_ids=buffer_ids[:], source_text=buffer_text))
        buffer_ids = []
        buffer_text = ""

    for line in sorted(filtered_lines, key=lambda item: item.id):
        if line.is_unclear:
            flush()
            sequence.append(UNCLEAR_MARK)
            continue
        buffer_ids.append(line.id)
        buffer_text += line.text
        if line.text.endswith(SENTENCE_END_CHARS):
            flush()
    flush()
    return sequence


def build_translation(filtered_lines: list[FilterResult], generator: TextGenerator) -> str:
    translated_parts: list[str] = []
    for item in build_chunks(filtered_lines):
        if item == UNCLEAR_MARK:
            translated_parts.append(UNCLEAR_MARK)
        else:
            translated_parts.append(generator.generate(item.source_text).strip())
    return "".join(translated_parts)
