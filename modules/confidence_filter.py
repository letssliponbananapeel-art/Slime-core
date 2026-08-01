from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .models import FilterResult, OcrLine, OcrPageResult


CONFIDENCE_THRESHOLD = 0.5
JP_CHAR_RATIO_THRESHOLD = 0.5
JP_CHAR_PATTERN = re.compile(r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]")


def jp_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(JP_CHAR_PATTERN.findall(text)) / len(text)


def judge_line(
    line: OcrLine | Mapping[str, Any],
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    jp_ratio_threshold: float = JP_CHAR_RATIO_THRESHOLD,
) -> FilterResult:
    ocr_line = line if isinstance(line, OcrLine) else OcrLine.from_mapping(line)
    ratio = jp_char_ratio(ocr_line.text)
    low_confidence = ocr_line.confidence < confidence_threshold
    non_japanese = ratio < jp_ratio_threshold
    if low_confidence and non_japanese:
        reason = "both"
    elif low_confidence:
        reason = "low_confidence"
    elif non_japanese:
        reason = "non_japanese"
    else:
        reason = None
    return FilterResult(
        id=ocr_line.id,
        text=ocr_line.text,
        confidence=ocr_line.confidence,
        is_unclear=reason is not None,
        reason=reason,
        jp_char_ratio=ratio,
        confidence_missing=ocr_line.confidence_missing,
    )


def filter_page(
    ocr_page: OcrPageResult | Mapping[str, Any],
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    jp_ratio_threshold: float = JP_CHAR_RATIO_THRESHOLD,
) -> list[FilterResult]:
    page = ocr_page if isinstance(ocr_page, OcrPageResult) else OcrPageResult.from_mapping(ocr_page)
    lines = page.contents[0] if page.contents else []
    return [
        judge_line(line, confidence_threshold=confidence_threshold, jp_ratio_threshold=jp_ratio_threshold)
        for line in lines
    ]
