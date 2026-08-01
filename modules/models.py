from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    if value is None:
        return default
    return bool(value)


def as_bounding_box(value: Any) -> list[list[int]]:
    if not isinstance(value, list):
        return []
    result: list[list[int]] = []
    for point in value:
        if not isinstance(point, list) or len(point) < 2:
            continue
        try:
            result.append([int(point[0]), int(point[1])])
        except (TypeError, ValueError):
            continue
    return result


@dataclass(frozen=True)
class OcrLine:
    id: int
    bounding_box: list[list[int]]
    is_vertical: bool
    text: str
    is_textline: bool
    confidence: float
    confidence_missing: bool = False

    @classmethod
    def from_mapping(cls, item: Mapping[str, Any], fallback_id: int = 0) -> "OcrLine":
        raw_confidence = item.get("confidence")
        confidence_missing = raw_confidence is None or raw_confidence == ""
        try:
            confidence = float(raw_confidence) if not confidence_missing else 0.0
        except (TypeError, ValueError):
            confidence = 0.0
            confidence_missing = True
        try:
            line_id = int(item.get("id", fallback_id))
        except (TypeError, ValueError):
            line_id = fallback_id
        return cls(
            id=line_id,
            bounding_box=as_bounding_box(item.get("boundingBox", item.get("bounding_box", []))),
            is_vertical=as_bool(item.get("isVertical", item.get("is_vertical")), True),
            text=str(item.get("text", "")),
            is_textline=as_bool(item.get("isTextline", item.get("is_textline")), True),
            confidence=confidence,
            confidence_missing=confidence_missing,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "boundingBox": self.bounding_box,
            "isVertical": self.is_vertical,
            "text": self.text,
            "isTextline": self.is_textline,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class OcrPageResult:
    contents: list[list[OcrLine]]
    imginfo: dict[str, Any]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "OcrPageResult":
        raw_contents = raw.get("contents", [])
        if raw_contents and isinstance(raw_contents, list) and isinstance(raw_contents[0], Mapping):
            raw_contents = [raw_contents]
        contents: list[list[OcrLine]] = []
        if isinstance(raw_contents, list):
            for block in raw_contents:
                if not isinstance(block, list):
                    continue
                lines = [
                    OcrLine.from_mapping(item, fallback_id=index)
                    for index, item in enumerate(block)
                    if isinstance(item, Mapping)
                ]
                contents.append(lines)
        imginfo = raw.get("imginfo", {})
        return cls(contents=contents or [[]], imginfo=dict(imginfo) if isinstance(imginfo, Mapping) else {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "contents": [[line.to_dict() for line in block] for block in self.contents],
            "imginfo": self.imginfo,
        }


@dataclass(frozen=True)
class FilterResult:
    id: int
    text: str
    confidence: float
    is_unclear: bool
    reason: str | None
    jp_char_ratio: float
    confidence_missing: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "confidence": self.confidence,
            "is_unclear": self.is_unclear,
            "reason": self.reason,
            "jp_char_ratio": self.jp_char_ratio,
            "confidence_missing": self.confidence_missing,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "FilterResult":
        reason = raw.get("reason")
        return cls(
            id=int(raw.get("id", -1)),
            text=str(raw.get("text", "")),
            confidence=float(raw.get("confidence", 0.0)),
            is_unclear=bool(raw.get("is_unclear", False)),
            reason=str(reason) if reason is not None else None,
            jp_char_ratio=float(raw.get("jp_char_ratio", 0.0)),
            confidence_missing=bool(raw.get("confidence_missing", False)),
        )


@dataclass(frozen=True)
class TranslationChunk:
    line_ids: list[int]
    source_text: str
