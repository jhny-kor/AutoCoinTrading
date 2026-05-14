"""
작업 요약
- 텔레그램 명령 리스너의 순수 명령/숫자/로그 포맷 helper 를 분리했다.
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_DOWN


LOW_SIGNAL_SECTION_MARKERS = (
    "아직",
    "없습니다",
    "비교할 수 없습니다",
    "집계할",
    "찾지 못해",
    "만들 수 없습니다",
)


def normalize_command(text: str) -> str:
    """입력 텍스트에서 텔레그램 명령만 정규화해 뽑는다."""
    first = text.strip().split()[0].lower()
    if "@" in first:
        first = first.split("@", 1)[0]
    if not first.startswith("/"):
        first = f"/{first}"
    return first


def split_telegram_text(text: str, limit: int = 3900) -> list[str]:
    """텔레그램 최대 길이를 넘지 않도록 문단 중심으로 메시지를 나눈다."""
    normalized = text.strip()
    if not normalized:
        return [""]
    if len(normalized) <= limit:
        return [normalized]

    chunks: list[str] = []
    current = ""

    for paragraph in normalized.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(paragraph) <= limit:
            current = paragraph
            continue

        for line in paragraph.splitlines():
            line = line.rstrip()
            candidate = line if not current else f"{current}\n{line}"
            if len(candidate) <= limit:
                current = candidate
                continue

            if current:
                chunks.append(current)
                current = ""

            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
            current = line

    if current:
        chunks.append(current)
    return chunks or [normalized[:limit]]


def send_text_in_chunks(notifier, text: str, limit: int = 3900) -> tuple[bool, str | None]:
    """긴 텔레그램 메시지를 여러 조각으로 나눠 순서대로 전송한다."""
    last_error: str | None = None
    sent_any = False
    for chunk in split_telegram_text(text, limit=limit):
        sent, error = notifier.send_message_detailed(chunk)
        if not sent:
            return False, error
        sent_any = True
        last_error = error
    return sent_any, last_error


def is_low_signal_section(section: str) -> bool:
    """복합 리포트에서 숨겨도 되는 빈 보조 섹션인지 판단한다."""
    lines = [line.strip() for line in section.strip().splitlines() if line.strip()]
    if not lines:
        return True
    if len(lines) == 1:
        return any(marker in lines[0] for marker in LOW_SIGNAL_SECTION_MARKERS)
    if len(lines) <= 2 and any(marker in lines[-1] for marker in LOW_SIGNAL_SECTION_MARKERS):
        return True
    return False


def join_report_sections(sections: list[str], *, skip_low_signal: bool = True) -> str:
    """텔레그램 복합 리포트 섹션을 저신호 문구 없이 합친다."""
    filtered: list[str] = []
    for section in sections:
        normalized = section.strip()
        if not normalized:
            continue
        if skip_low_signal and is_low_signal_section(normalized):
            continue
        filtered.append(normalized)
    return "\n\n".join(filtered)


def format_number(value: float, decimals: int = 4) -> str:
    """지정 소수점 자리수와 천 단위 쉼표를 적용한 숫자 문자열을 만든다."""
    return f"{value:,.{decimals}f}"


def format_number_trunc(value: float, decimals: int = 4) -> str:
    """지정 소수점 자리수에서 절사 기준으로 천 단위 쉼표 문자열을 만든다."""
    quantizer = Decimal("1") if decimals <= 0 else Decimal(f"1.{'0' * decimals}")
    truncated = Decimal(str(value)).quantize(quantizer, rounding=ROUND_DOWN)
    return f"{truncated:,.{decimals}f}"


def safe_float(value) -> float | None:
    """None 이나 빈 값을 제외하고 안전하게 float 로 변환한다."""
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_symbol_from_log_line(line: str) -> str | None:
    """운영 로그 한 줄에서 심볼 표기를 추출한다."""
    symbol_match = re.search(r"\[([A-Z0-9]+/[A-Z0-9]+)\]", line)
    if symbol_match:
        return symbol_match.group(1)
    return None


def format_numeric_token_for_telegram(token: str) -> str:
    """숫자 토큰에 세 자리 쉼표를 넣되 소수점 자릿수는 유지한다."""
    if not token:
        return token

    sign = ""
    raw = token
    if raw.startswith("-"):
        sign = "-"
        raw = raw[1:]

    if "." in raw:
        whole, fraction = raw.split(".", 1)
        if not whole:
            whole = "0"
        return f"{sign}{int(whole):,}.{fraction}"
    return f"{sign}{int(raw):,}"


def format_symbol_badge(symbol: str) -> str:
    """텔레그램 리포트에서 심볼 앞에 초록 원을 붙인다."""
    cleaned = symbol.strip()
    return f"🟢 {cleaned}" if cleaned else "🟢"


def format_recent_log_line_for_telegram(line: str) -> str:
    """대괄호 안 텍스트는 유지하고, 그 밖의 숫자만 텔레그램용으로 포맷한다."""
    parts = re.split(r"(\[[^\]]*\])", line)
    formatted: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("[") and part.endswith("]"):
            formatted.append(part)
            continue
        formatted.append(
            re.sub(
                r"-?\d+(?:\.\d+)?",
                lambda match: format_numeric_token_for_telegram(match.group(0)),
                part,
            )
        )
    return "".join(formatted)
