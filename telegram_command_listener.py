"""
수정 요약
- /status, /positions, /analysis, 일일/주간 리포트에 복구 포지션 상태와 일일 손실 제한 상태를 함께 보여주도록 확장
- 백테스트 대비 실거래 설명 섹션에 누락 심볼 안내와 더 구체적인 차이 설명을 함께 넣도록 보강
- /pnl 과 기간 손익 요약의 KRW 금액은 반올림이 아니라 절사 기준으로 표시하도록 정리했다.
- /regime 명령으로 심볼별 현재 레짐과 핵심 근거 숫자를 바로 볼 수 있도록 추가했다.
- /pnl 과 기간 손익 요약에서 KRW, USDT 손익 문구를 한국어 기준으로 더 자연스럽게 보이도록 정리했다.
- 최근 체결 내역이 로그 제목만이 아니라 금액, 수량, 손익까지 보이도록 trade_history 기준으로 바꿨다.
- 주간 리포트에도 현재 시장 해석과 전략 추천 섹션을 함께 넣어 /analysis 와 읽는 기준을 맞췄다.
- /analysis 에 최신 시장 숫자 요약과 현재 로그 기준 추천 전략을 함께 보여주는 섹션을 추가했다.
- 에러 알림 메시지에 붙는 승인형 버튼(재기동/상세 보기/수정 요청/무시)을 처리하는 텔레그램 callback 흐름을 추가
- /analysis 와 /weekly 에 순익 보호 익절 발생 건수와 순손익을 바로 확인할 수 있는 전용 요약 섹션을 추가
- /analysis 와 주간 리포트의 거래 품질 섹션에 API 지연, 슬리피지, 체결 비율 같은 주문 실행 품질 요약도 함께 표시하도록 확장
- /pnl 이 과거 체결도 가능한 범위에서 순손익으로 재추정해 통화별 손순익 집계가 최대한 완전하게 보이도록 보강
- /analysis 와 정기 리포트에 거래 품질 요약, 필터 기준 부족 폭, 시간대 성과 요약까지 함께 넣도록 확장
- 텔레그램 명령 리스너 자체의 런타임 예외도 즉시 텔레그램으로 알리도록 보강
- /pnl 이 프로그램별 최신 문구가 아니라 KRW, USDT 기준 오늘 누적 손익을 체결 이력에서 다시 합산해 보여주도록 개선
- /last 에서 가격/수량 같은 숫자는 텔레그램용으로 세 자리마다 쉼표를 넣어 가독성을 개선
- /last 에서 심볼별 로그가 이미 있으면 의미 없는 `공통` 묶음은 숨기도록 정리
- /last 명령이 알트 봇에서 심볼별 최근 로그를 따로 묶어 보여주도록 개선
- 오늘 스킵 사유 요약이 BTC 전용 봇 문구를 놓치지 않도록 구조화 전략 로그 우선 집계로 개선
- reason 코드와 actual/required 값을 기준으로 스킵 사유를 한글 라벨로 안정적으로 묶도록 개선
- 기존 텍스트 로그 패턴 집계는 구조화 로그가 없을 때만 사용하는 보조 경로로 유지
- 운영 대상 심볼 목록을 알트 공통 설정과 자동 연동하도록 재구조화
- /positions 응답에 현재 추정 손익률을 함께 표시하고, 수익/손실은 색상 대신 원형 표시로 구분하도록 개선
- 정기 리포트에 최근 1주 거래량 기준 신규 후보 코인 3개씩을 거래소별로 함께 보내도록 확장

텔레그램 명령 리스너

- 텔레그램에서 /status, /positions, /pnl, /analysis, /regime, /weekly, /last 명령을 받아 응답한다.
- 상태 조회는 bot_manager 의 관리 대상 상태 문자열을 재사용한다.
- 포지션 조회는 각 거래소 API 를 호출해 현재 잔고와 대략적인 평가 금액을 보여준다.
- 분석 조회는 analyze_logs 의 요약 함수를 재사용한다.
- 최근 로그 조회는 프로그램별 로그 파일 끝부분을 짧게 묶어서 보여준다.
- /test 명령과 즉시 테스트 전송 옵션으로 텔레그램 연결 상태를 점검할 수 있다.
- 아침 8시, 오후 12시, 저녁 6시, 밤 9시에 일일 리포트를 자동 전송할 수 있다.
- 매주 월요일 오전 9시에 최근 7일 기준 주간 리포트를 자동 전송할 수 있다.
- 일일 리포트에 최근 체결 내역과 오늘 스킵 사유 요약을 함께 포함한다.
- 시장 로그 분석과 전략 퍼널 분석을 함께 요약해 한눈에 보기 쉽게 정리한다.
- 거래소 조회 실패를 timeout, 권한 부족, 인증 실패 단계로 나눠 바로 원인 추정이 가능하게 개선했다.
- 텔레그램 polling 과 응답 전송 실패도 상세 사유를 로그에 남기도록 개선했다.

가능한 모든 텔레그램 명령
- /start
- /help
- /test
- /status
- /positions
- /pnl
- /analysis
- /regime
- /weekly
- /last

가능한 실행 명령
- .venv/bin/python telegram_command_listener.py
- .venv/bin/python telegram_command_listener.py --send-test
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import ccxt
from dotenv import load_dotenv

import analyze_logs
import analyze_strategy_logs
import bot_manager
from btc_trend_settings import load_btc_trend_settings
from incident_manager import find_incident, update_incident_status
from bot_logger import BotLogger
from log_path_utils import iter_files, latest_file, read_all_lines
from ma_crossover_bot import (
    create_okx_client,
    fetch_ohlcv as fetch_okx_ohlcv,
    get_spot_balances as get_okx_spot_balances,
    load_config as load_okx_config,
)
from market_regime_guard import classify_symbol_regime
from state_recovery import (
    load_program_daily_realized_pnl_quote,
    restore_program_position_states,
)
from strategy_settings import load_alt_symbols, load_managed_symbols, load_strategy_settings
from telegram_notifier import load_telegram_notifier
from telegram_notifier import format_telegram_request_error
from telegram_notifier import format_telegram_text_numbers
from trade_history_logger import estimate_round_trip_net_pnl
from upbit_ma_crossover_bot import (
    create_upbit_client,
    fetch_ohlcv as fetch_upbit_ohlcv,
    get_spot_balances as get_upbit_spot_balances,
    load_config as load_upbit_config,
)

TRADE_EVENT_RE = re.compile(
    r"^\[(?P<ts>[^\]]+)\] \[(?P<symbol>[^\]]+)\] (?P<title>.+주문 체결)$"
)

SKIP_REASON_PATTERNS = [
    ("신호 약함", "신호가 약합니다."),
    ("상위 타임프레임 불일치", "상위 타임프레임"),
    ("거래량 부족", "거래량이 부족하여 신규 매수를 보류합니다."),
    ("변동성 범위 이탈", "변동성이 기준 범위를 벗어나 신규 매수를 보류합니다."),
    ("추가 매수 조건 미충족", "추가 매수 조건 미충족"),
    ("최소 익절률 미달", "최소 익절률"),
    ("주문 금액 부족", "주문 금액이"),
    ("일일 손실 제한", "일일 최대 손실 제한에 도달하여 신규 매수를 중단합니다."),
    ("쿨다운", "최근 거래 후 쿨다운 중입니다."),
    ("조건 미충족 대기", "주문 조건에 해당하지 않아 대기합니다."),
    ("조건 미충족 대기", "BTC EMA 전략 조건에 해당하지 않아 대기합니다."),
]

PROGRAM_LOG_SOURCES = [
    ("OKX 알트", "ma_crossover_bot.log"),
    ("업비트 알트", "upbit_ma_crossover_bot.log"),
    ("OKX BTC", "okx_btc_ema_trend_bot.log"),
    ("업비트 BTC", "upbit_btc_ema_trend_bot.log"),
]

PROGRAM_STRUCTURE_SOURCES = [
    ("OKX 알트", "ma_crossover_bot"),
    ("업비트 알트", "upbit_ma_crossover_bot"),
    ("OKX BTC", "okx_btc_ema_trend_bot"),
    ("업비트 BTC", "upbit_btc_ema_trend_bot"),
]

PROGRAM_LABELS = {
    "ma_crossover_bot": "OKX 알트",
    "upbit_ma_crossover_bot": "업비트 알트",
    "okx_btc_ema_trend_bot": "OKX BTC",
    "upbit_btc_ema_trend_bot": "업비트 BTC",
}

PROGRAM_STRATEGY_TYPES = {
    "ma_crossover_bot": "alt",
    "upbit_ma_crossover_bot": "alt",
    "okx_btc_ema_trend_bot": "btc",
    "upbit_btc_ema_trend_bot": "btc",
}

PROGRAM_EXCHANGES = {
    "ma_crossover_bot": "OKX",
    "upbit_ma_crossover_bot": "UPBIT",
    "okx_btc_ema_trend_bot": "OKX",
    "upbit_btc_ema_trend_bot": "UPBIT",
}

OKX_TICKERS_URL = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
OKX_CANDLES_URL = "https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar=1D&limit=7"
UPBIT_TICKER_ALL_URL = "https://api.upbit.com/v1/ticker/all?quote_currencies=KRW"
UPBIT_CANDLES_URL = "https://api.upbit.com/v1/candles/days?market={market}&count=7"
VOLUME_CANDIDATE_COUNT = 3
STABLE_BASES = {"USDT", "USDC", "USDC.e", "USDD", "DAI"}
WEEKDAY_NAME_TO_INDEX = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


@dataclass(frozen=True)
class ListenerSettings:
    """텔레그램 명령 리스너 설정."""

    poll_interval_sec: int
    offset_path: Path
    report_state_path: Path
    analysis_log_dir: Path
    okx_symbols: list[str]
    upbit_symbols: list[str]
    recent_log_line_count: int
    daily_report_enabled: bool
    morning_report_hour: int
    noon_report_hour: int
    evening_report_hour: int
    night_report_hour: int
    weekly_report_enabled: bool
    weekly_report_weekday: int
    weekly_report_hour: int


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_listener_settings() -> ListenerSettings:
    """환경 변수에서 리스너 설정을 읽는다."""
    load_dotenv()

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    return ListenerSettings(
        poll_interval_sec=int(os.getenv("TELEGRAM_COMMAND_POLL_INTERVAL_SEC", "5")),
        offset_path=log_dir / "telegram_command_listener.offset",
        report_state_path=log_dir / "telegram_daily_report_state.json",
        analysis_log_dir=Path(os.getenv("ANALYSIS_LOG_DIR", "analysis_logs")),
        okx_symbols=load_managed_symbols("okx"),
        upbit_symbols=load_managed_symbols("upbit"),
        recent_log_line_count=int(os.getenv("TELEGRAM_RECENT_LOG_LINE_COUNT", "5")),
        daily_report_enabled=parse_bool(
            os.getenv("TELEGRAM_DAILY_REPORT_ENABLED", "true"),
            default=True,
        ),
        morning_report_hour=int(os.getenv("TELEGRAM_DAILY_REPORT_MORNING_HOUR", "8")),
        noon_report_hour=int(os.getenv("TELEGRAM_DAILY_REPORT_NOON_HOUR", "12")),
        evening_report_hour=int(os.getenv("TELEGRAM_DAILY_REPORT_EVENING_HOUR", "18")),
        night_report_hour=int(os.getenv("TELEGRAM_DAILY_REPORT_NIGHT_HOUR", "21")),
        weekly_report_enabled=parse_bool(
            os.getenv("TELEGRAM_WEEKLY_REPORT_ENABLED", "true"),
            default=True,
        ),
        weekly_report_weekday=WEEKDAY_NAME_TO_INDEX.get(
            os.getenv("TELEGRAM_WEEKLY_REPORT_WEEKDAY", "MON").strip().upper(),
            0,
        ),
        weekly_report_hour=int(os.getenv("TELEGRAM_WEEKLY_REPORT_HOUR", "9")),
    )


def telegram_api_request(
    bot_token: str,
    method: str,
    payload: dict | None = None,
    timeout: int = 30,
) -> tuple[dict | None, str | None]:
    """텔레그램 Bot API 를 호출한다."""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        return None, format_telegram_request_error(exc)

    try:
        result = json.loads(raw_body)
    except (ValueError, json.JSONDecodeError) as exc:
        return None, format_telegram_request_error(exc)

    if isinstance(result, dict) and result.get("ok") is False:
        description = result.get("description")
        if isinstance(description, str) and description.strip():
            return None, description.strip()
        return None, "텔레그램 API 가 요청을 거부했습니다."

    return result, None


def get_updates(
    bot_token: str, offset: int, timeout: int = 20
) -> tuple[list[dict], str | None]:
    """새 텔레그램 업데이트 목록을 가져온다."""
    query = urllib.parse.urlencode({"offset": offset, "timeout": timeout})
    result, error = telegram_api_request(
        bot_token,
        f"getUpdates?{query}",
        payload=None,
        timeout=timeout + 5,
    )
    if error:
        return [], error
    if not result:
        return [], "텔레그램 업데이트 응답이 비어 있습니다."
    return result.get("result", []), None


def load_offset(path: Path) -> int:
    """마지막으로 처리한 update offset 을 읽는다."""
    if not path.exists():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return 0


def save_offset(path: Path, offset: int):
    """마지막으로 처리한 update offset 을 저장한다."""
    path.write_text(str(offset), encoding="utf-8")


def initialize_offset_if_needed(
    bot_token: str, settings: ListenerSettings, logger: BotLogger
) -> int:
    """초기 실행 시 과거 메시지를 건너뛰도록 offset 을 맞춘다."""
    current_offset = load_offset(settings.offset_path)
    if current_offset > 0:
        return current_offset

    updates, error = get_updates(bot_token, offset=0, timeout=0)
    if error:
        logger.log(f"초기 텔레그램 offset 조회 실패: {error}")
        return 0
    if not updates:
        return 0

    next_offset = max(update["update_id"] for update in updates) + 1
    save_offset(settings.offset_path, next_offset)
    logger.log(
        f"기존 텔레그램 메시지 {len(updates)}건은 재처리하지 않도록 offset 을 {next_offset} 으로 맞췄습니다."
    )
    return next_offset


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


def classify_exchange_error(exc: Exception) -> tuple[str, str]:
    """거래소 예외를 분류하고 점검 포인트를 반환한다."""
    raw_message = str(exc).strip() or repr(exc)
    lowered = raw_message.lower()

    if (
        isinstance(exc, ccxt.PermissionDenied)
        or "no permission" in lowered
        or "out_of_scope" in lowered
        or "권한" in raw_message
    ):
        return "권한 부족", "API 키 권한, 계정 권한, IP 화이트리스트를 확인해 주세요."

    if isinstance(exc, ccxt.AuthenticationError):
        return "인증 실패", "API 키, 시크릿, 패스프레이즈 입력값을 다시 확인해 주세요."

    if isinstance(exc, ccxt.RequestTimeout) or "timed out" in lowered or "timeout" in lowered:
        return "타임아웃", "거래소 응답 지연 또는 일시적인 네트워크 혼잡 가능성이 큽니다."

    if isinstance(exc, ccxt.NetworkError):
        return "네트워크", "인터넷 연결 또는 거래소 API 접속 상태를 확인해 주세요."

    return "기타 오류", "원문 에러를 기준으로 해당 거래소 API 상태를 직접 확인해 주세요."


def format_exchange_error_text(
    exchange_name: str,
    action: str,
    exc: Exception,
    *,
    symbol: str | None = None,
) -> str:
    """거래소 조회 실패를 텔레그램 메시지용 진단 문구로 만든다."""
    error_type, guidance = classify_exchange_error(exc)
    raw_message = str(exc).strip() or repr(exc)
    target = f"{symbol} {action}" if symbol else action
    return "\n".join(
        [
            f"- {target} 실패 [{error_type}]",
            f"원인 추정: {guidance}",
            f"세부: {raw_message}",
        ]
    )


def build_help_text() -> str:
    """지원 명령 목록을 반환한다."""
    return (
        "사용 가능한 명령\n"
        "- /test : 텔레그램 응답 테스트\n"
        "- /status : 현재 봇 실행 상태\n"
        "- /positions : 현재 잔고와 포지션 요약\n"
        "- /pnl : 오늘 누적 실현 손익 요약\n"
        "- /analysis : 최근 분석 로그 요약\n"
        "- /regime : 심볼별 현재 레짐 요약\n"
        "- /weekly : 최근 7일 기준 주간 리포트\n"
        "- /last : 최근 운영 로그 확인\n"
        "- /help : 도움말"
    )


def parse_local_timestamp(raw: str) -> datetime | None:
    """로컬 시각 문자열을 datetime 으로 안전하게 변환한다."""
    try:
        if not raw:
            return None
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is not None:
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def is_in_recent_days(raw: str, days: int, *, now: datetime | None = None) -> bool:
    """지정된 최근 일수 범위 안의 시각인지 확인한다."""
    parsed = parse_local_timestamp(raw)
    if parsed is None:
        return False
    current = now or datetime.now()
    lower_bound = current - timedelta(days=days)
    return lower_bound <= parsed <= current


def build_positions_text(settings: ListenerSettings) -> str:
    """현재 거래소별 잔고와 포지션 요약을 만든다."""
    sections = ["현재 포지션 요약"]
    sections.append(build_okx_positions_text(settings.okx_symbols))
    sections.append(build_upbit_positions_text(settings.upbit_symbols))
    sections.append(build_recovered_position_state_text(settings))
    return "\n\n".join(sections)


def load_recovered_position_rows(settings: ListenerSettings) -> list[dict[str, object]]:
    """프로그램별 복구 포지션 상태를 요약 행으로 반환한다."""
    now_ts = time.time()
    alt_settings = load_strategy_settings("OKX_MIN_BUY_ORDER_VALUE", 1.0)
    btc_settings = load_btc_trend_settings()
    targets = [
        ("ma_crossover_bot", settings.okx_symbols),
        ("upbit_ma_crossover_bot", settings.upbit_symbols),
        ("okx_btc_ema_trend_bot", ["BTC/USDT"]),
        ("upbit_btc_ema_trend_bot", ["BTC/KRW"]),
    ]
    rows: list[dict[str, object]] = []
    for program_name, symbols in targets:
        strategy_type = PROGRAM_STRATEGY_TYPES.get(program_name, "alt")
        recovered = restore_program_position_states(program_name, symbols)
        daily_realized_pnl_quote = load_program_daily_realized_pnl_quote(program_name)
        for symbol, state in recovered.items():
            if state.average_entry_price is None:
                continue
            if strategy_type == "btc":
                base_cooldown_remaining = max(
                    0.0,
                    btc_settings.min_trade_interval_sec - (now_ts - state.last_trade_at_ts),
                )
                stop_cooldown_remaining = max(
                    0.0,
                    btc_settings.stop_loss_reentry_cooldown_sec - (now_ts - state.last_stop_loss_at_ts),
                )
                profit_cooldown_remaining = max(
                    0.0,
                    btc_settings.profit_exit_reentry_cooldown_sec - (now_ts - state.last_profit_exit_at_ts),
                )
                cooldown_remaining = max(
                    base_cooldown_remaining,
                    stop_cooldown_remaining,
                    profit_cooldown_remaining,
                )
            else:
                trade_cooldown_remaining = max(
                    0.0,
                    alt_settings.min_trade_interval_sec - (now_ts - state.last_trade_at_ts),
                )
                partial_tp_cooldown_remaining = max(
                    0.0,
                    alt_settings.partial_take_profit_reentry_cooldown_sec
                    - (now_ts - state.last_partial_take_profit_at_ts),
                ) if state.last_partial_take_profit_at_ts > 0 else 0.0
                cooldown_remaining = max(
                    trade_cooldown_remaining,
                    partial_tp_cooldown_remaining,
                )
            rows.append(
                {
                    "program_name": program_name,
                    "label": PROGRAM_LABELS.get(program_name, program_name),
                    "exchange": PROGRAM_EXCHANGES.get(program_name, ""),
                    "strategy_type": strategy_type,
                    "symbol": symbol,
                    "average_entry_price": state.average_entry_price,
                    "cycle_buy_count": state.cycle_buy_count,
                    "opened_at_ts": state.opened_at_ts,
                    "highest_price_since_entry": state.highest_price_since_entry,
                    "lowest_price_since_entry": state.lowest_price_since_entry,
                    "partial_take_profit_done": state.partial_take_profit_done,
                    "partial_stop_loss_done": state.partial_stop_loss_done,
                    "trailing_armed": state.trailing_armed,
                    "trailing_activation_price": state.trailing_activation_price,
                    "cooldown_remaining_sec": cooldown_remaining,
                    "daily_realized_pnl_quote": daily_realized_pnl_quote,
                }
            )
    rows.sort(key=lambda row: (str(row["label"]), str(row["symbol"])))
    return rows


def build_recovered_position_state_text(settings: ListenerSettings, limit: int = 8) -> str:
    """복구 포지션 상태와 주요 제약을 텔레그램용 문구로 만든다."""
    rows = load_recovered_position_rows(settings)
    if not rows:
        return "복구 상태 요약\n- 현재 체결 이력 기준으로 복구된 활성 포지션 상태가 없습니다."

    lines = ["복구 상태 요약"]
    for row in rows[:limit]:
        symbol = str(row["symbol"])
        quote = symbol.split("/", 1)[1] if "/" in symbol else ""
        decimals = 0 if quote == "KRW" else 4
        avg_entry_price = float(row["average_entry_price"])
        highest_price = safe_float(row.get("highest_price_since_entry"))
        lowest_price = safe_float(row.get("lowest_price_since_entry"))
        cooldown_remaining_sec = int(float(row.get("cooldown_remaining_sec") or 0.0))
        daily_realized_pnl_quote = float(row["daily_realized_pnl_quote"])
        detail_parts = [
            f"avg {format_number(avg_entry_price, decimals)}",
            f"활성 레그 {int(row['cycle_buy_count'])}회",
            f"오늘 손익 {format_number_trunc(daily_realized_pnl_quote, decimals)} {quote}",
        ]
        if highest_price is not None and lowest_price is not None:
            detail_parts.append(
                f"고저 {format_number(highest_price, decimals)} / {format_number(lowest_price, decimals)}"
            )
        if row["strategy_type"] == "btc":
            detail_parts.append(
                f"트레일링 {'ON' if row['trailing_armed'] else 'OFF'}"
            )
            trailing_activation_price = safe_float(row.get("trailing_activation_price"))
            if trailing_activation_price is not None:
                detail_parts.append(
                    f"활성가 {format_number(trailing_activation_price, decimals)}"
                )
        else:
            detail_parts.append(
                f"부분익절 {'완료' if row['partial_take_profit_done'] else '대기'}"
            )
            if row["partial_stop_loss_done"]:
                detail_parts.append("부분손절 완료")
        if cooldown_remaining_sec > 0:
            detail_parts.append(f"쿨다운 {cooldown_remaining_sec}초 남음")
        lines.append(f"- {row['label']} | {symbol} | " + " | ".join(detail_parts))
    return "\n".join(lines)


def build_runtime_guard_status_text(settings: ListenerSettings) -> str:
    """복구 포지션 수와 일일 손실 제한 상태를 요약한다."""
    rows = load_recovered_position_rows(settings)
    rows_by_program: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        rows_by_program.setdefault(str(row["program_name"]), []).append(row)

    config_rows = [
        ("ma_crossover_bot", "OKX 알트", "USDT", float(os.getenv("OKX_MAX_DAILY_LOSS_QUOTE", "5.0"))),
        ("upbit_ma_crossover_bot", "업비트 알트", "KRW", float(os.getenv("UPBIT_MAX_DAILY_LOSS_QUOTE", "5000"))),
        ("okx_btc_ema_trend_bot", "OKX BTC", "USDT", float(os.getenv("OKX_MAX_DAILY_LOSS_QUOTE", "5.0"))),
        ("upbit_btc_ema_trend_bot", "업비트 BTC", "KRW", float(os.getenv("UPBIT_MAX_DAILY_LOSS_QUOTE", "5000"))),
    ]

    lines = ["운영 제한 요약"]
    for program_name, label, quote, max_daily_loss_quote in config_rows:
        active_rows = rows_by_program.get(program_name, [])
        active_count = len(active_rows)
        daily_realized_pnl_quote = load_program_daily_realized_pnl_quote(program_name)
        limit_reached = daily_realized_pnl_quote <= -max_daily_loss_quote
        decimals = 0 if quote == "KRW" else 4
        lines.append(
            f"- {label} | 복구 포지션 {active_count}개 | "
            f"오늘 손익 {format_number_trunc(daily_realized_pnl_quote, decimals)} {quote} | "
            f"손실 제한 {'도달' if limit_reached else '정상'} "
            f"(기준 -{format_number(max_daily_loss_quote, decimals)} {quote})"
        )
    return "\n".join(lines)


def load_latest_backtest_comparison_rows(settings: ListenerSettings) -> list[dict[str, object]]:
    """관리 심볼 기준 최신 백테스트 비교 결과를 읽는다."""
    managed_symbols = set(settings.okx_symbols + settings.upbit_symbols)
    comparison_paths = iter_files("reports/backtests", "comparison.json")
    latest_by_key: dict[tuple[str, str], tuple[float, dict[str, object]]] = {}
    for path in comparison_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        filters = payload.get("filters", {})
        if not isinstance(filters, dict):
            continue
        symbol = str(filters.get("symbol", "")).strip()
        program_name = str(filters.get("program_name", "")).strip()
        if not symbol or symbol not in managed_symbols:
            continue
        if not program_name:
            continue
        key = (program_name, symbol)
        mtime = path.stat().st_mtime
        current = latest_by_key.get(key)
        if current is None or mtime > current[0]:
            latest_by_key[key] = (mtime, payload)

    rows = [item[1] for item in latest_by_key.values()]
    rows.sort(
        key=lambda payload: (
            str(payload.get("filters", {}).get("program_name", "")),
            str(payload.get("filters", {}).get("symbol", "")),
        )
    )
    return rows


def build_backtest_comparison_text(settings: ListenerSettings, limit: int = 6) -> str:
    """백테스트 대비 실거래 설명 섹션을 만든다."""
    rows = load_latest_backtest_comparison_rows(settings)
    if not rows:
        return (
            "백테스트 대비 실거래 설명\n"
            "- 아직 comparison.json 이 없습니다. backtest_replay.py 와 compare_backtest_to_live.py 를 먼저 실행해 주세요."
        )

    lines = ["백테스트 대비 실거래 설명"]
    covered_symbols: set[str] = set()
    for payload in rows[:limit]:
        filters = payload.get("filters", {}) if isinstance(payload.get("filters"), dict) else {}
        backtest = payload.get("backtest", {}) if isinstance(payload.get("backtest"), dict) else {}
        live = payload.get("live", {}) if isinstance(payload.get("live"), dict) else {}
        comments = payload.get("comments", []) if isinstance(payload.get("comments"), list) else []
        symbol = str(filters.get("symbol", ""))
        program_name = str(filters.get("program_name", ""))
        covered_symbols.add(symbol)
        label = PROGRAM_LABELS.get(program_name, program_name)
        backtest_sell_count = int(backtest.get("sell_count", 0) or 0)
        live_sell_count = int(live.get("sell_count", 0) or 0)
        backtest_win_rate = float(backtest.get("win_rate_pct", 0.0) or 0.0)
        live_win_rate = float(live.get("win_rate_pct", 0.0) or 0.0)
        backtest_avg_pnl = float(backtest.get("avg_net_realized_pnl_pct", 0.0) or 0.0)
        live_avg_pnl = float(live.get("avg_net_realized_pnl_pct", 0.0) or 0.0)
        backtest_total_quote = float(backtest.get("total_net_realized_pnl_quote", 0.0) or 0.0)
        live_total_quote = float(live.get("total_net_realized_pnl_quote", 0.0) or 0.0)
        backtest_top_reason = (
            backtest.get("top_exit_reasons", [("-", 0)])[0][0]
            if backtest.get("top_exit_reasons")
            else "-"
        )
        live_top_reason = (
            live.get("top_exit_reasons", [("-", 0)])[0][0]
            if live.get("top_exit_reasons")
            else "-"
        )
        lines.append(
            f"- {label} | {symbol} | "
            f"백테스트 매도 {backtest_sell_count}건 / 실거래 매도 {live_sell_count}건 | "
            f"승률 차이 {live_win_rate - backtest_win_rate:+.2f}%p | "
            f"평균 순손익률 차이 {live_avg_pnl - backtest_avg_pnl:+.4f}%p"
        )
        lines.append(
            f"  성과: 백테스트 총 순손익 {backtest_total_quote:.4f}, "
            f"실거래 총 순손익 {live_total_quote:.4f}"
        )
        lines.append(
            f"  종료 사유: 백테스트 대표 `{backtest_top_reason}` / "
            f"실거래 대표 `{live_top_reason}`"
        )
        if comments:
            lines.append(f"  해석: {' / '.join(str(comment) for comment in comments[:4])}")
    missing_symbols = sorted(set(settings.okx_symbols + settings.upbit_symbols) - covered_symbols)
    if missing_symbols:
        lines.append(f"- 비교 결과가 아직 없는 심볼: {', '.join(missing_symbols[:6])}")
        sample_symbol = missing_symbols[0]
        sample_exchange = "upbit" if sample_symbol.endswith("/KRW") else "okx"
        sample_strategy = "btc" if sample_symbol.startswith("BTC/") else "alt"
        sample_slug = sample_symbol.replace("/", "_").replace("-", "_").lower()
        lines.append(
            "  권장 실행: "
            f".venv/bin/python backtest_report_runner.py snapshot --label auto_compare_{sample_slug} "
            f"--symbols {sample_symbol} --exchanges {sample_exchange}"
        )
    return "\n".join(lines)


def load_latest_entry_prices() -> dict[tuple[str, str], float]:
    """체결 이력에서 거래소/심볼별 최신 추정 진입가를 읽는다."""
    latest_prices: dict[tuple[str, str], float] = {}
    latest_ts: dict[tuple[str, str], str] = {}

    for path in iter_files("trade_logs", "trade_history.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                continue

            exchange = str(record.get("exchange", "")).strip().upper()
            symbol = str(record.get("symbol", "")).strip()
            estimated_entry_price = record.get("estimated_entry_price")
            recorded_at = str(record.get("recorded_at_local", ""))

            if not exchange or not symbol or estimated_entry_price in (None, ""):
                continue

            try:
                price = float(estimated_entry_price)
            except (TypeError, ValueError):
                continue

            key = (exchange, symbol)
            if key not in latest_ts or recorded_at >= latest_ts[key]:
                latest_ts[key] = recorded_at
                latest_prices[key] = price

    return latest_prices


def format_pnl_badge(pnl_pct: float) -> str:
    """손익률을 텔레그램용 짧은 배지 문자열로 만든다."""
    if pnl_pct > 0:
        return f"🔴 +{pnl_pct:.2f}%"
    if pnl_pct < 0:
        return f"🔵 {pnl_pct:.2f}%"
    return "⚪ 0.00%"


def build_okx_positions_text(symbols: list[str]) -> str:
    """OKX 현재 잔고와 포지션 요약을 만든다."""
    try:
        config = load_okx_config()
        exchange = create_okx_client(config)
        latest_entry_prices = load_latest_entry_prices()
        recovered_entry_prices: dict[str, float] = {}
        for program_name, target_symbols in (
            ("ma_crossover_bot", [symbol for symbol in symbols if symbol != "BTC/USDT"]),
            ("okx_btc_ema_trend_bot", [symbol for symbol in symbols if symbol == "BTC/USDT"]),
        ):
            for symbol, state in restore_program_position_states(program_name, target_symbols).items():
                if state.average_entry_price is not None:
                    recovered_entry_prices[symbol] = state.average_entry_price
        lines = ["[OKX]"]
        seen_quotes: set[str] = set()
        meaningful_position_count = 0

        for symbol in symbols:
            base, quote = symbol.split("/", 1)
            try:
                base_free, quote_free = get_okx_spot_balances(exchange, base, quote)
            except Exception as exc:
                lines.append(
                    format_exchange_error_text("OKX", "잔고 조회", exc, symbol=symbol)
                )
                continue

            if quote not in seen_quotes:
                lines.append(f"- 보유 {quote}: {format_number(quote_free, 4)}")
                seen_quotes.add(quote)

            try:
                ticker_ohlcv = fetch_okx_ohlcv(exchange, symbol, timeframe="1m", limit=1)
                last_close = ticker_ohlcv[-1][4]
            except Exception as exc:
                if base_free > 0:
                    lines.append(
                        f"- {symbol}: {format_number(base_free, 6)} {base} | 현재가 조회 실패"
                    )
                lines.append(
                    format_exchange_error_text("OKX", "현재가 조회", exc, symbol=symbol)
                )
                continue

            estimated_value = base_free * last_close
            if estimated_value >= 0.1:
                meaningful_position_count += 1
                line = (
                    f"- {symbol}: {format_number(base_free, 6)} {base} | "
                    f"현재가 {format_number(last_close, 4)} | "
                    f"평가 {format_number(estimated_value, 4)} {quote}"
                )
                entry_price = recovered_entry_prices.get(symbol)
                if entry_price is None:
                    entry_price = latest_entry_prices.get(("OKX", symbol))
                if entry_price and entry_price > 0:
                    pnl_pct = ((last_close - entry_price) / entry_price) * 100
                    line += (
                        f" | 진입가 {format_number(entry_price, 4)} | "
                        f"현재 손익 {format_pnl_badge(pnl_pct)}"
                    )
                lines.append(line)

        if meaningful_position_count == 0:
            lines.append("- 의미 있는 코인 보유 포지션 없음")
        return "\n".join(lines)
    except Exception as exc:
        return "[OKX]\n" + format_exchange_error_text("OKX", "초기화", exc)


def build_upbit_positions_text(symbols: list[str]) -> str:
    """업비트 현재 잔고와 포지션 요약을 만든다."""
    try:
        config = load_upbit_config()
        exchange = create_upbit_client(config)
        latest_entry_prices = load_latest_entry_prices()
        recovered_entry_prices: dict[str, float] = {}
        for program_name, target_symbols in (
            ("upbit_ma_crossover_bot", [symbol for symbol in symbols if symbol != "BTC/KRW"]),
            ("upbit_btc_ema_trend_bot", [symbol for symbol in symbols if symbol == "BTC/KRW"]),
        ):
            for symbol, state in restore_program_position_states(program_name, target_symbols).items():
                if state.average_entry_price is not None:
                    recovered_entry_prices[symbol] = state.average_entry_price
        lines = ["[UPBIT]"]
        seen_quotes: set[str] = set()
        meaningful_position_count = 0

        for symbol in symbols:
            base, quote = symbol.split("/", 1)
            try:
                base_free, quote_free = get_upbit_spot_balances(exchange, base, quote)
            except Exception as exc:
                lines.append(
                    format_exchange_error_text("UPBIT", "잔고 조회", exc, symbol=symbol)
                )
                continue

            if quote not in seen_quotes:
                lines.append(f"- 보유 {quote}: {format_number(quote_free, 0)}")
                seen_quotes.add(quote)

            try:
                ticker_ohlcv = fetch_upbit_ohlcv(exchange, symbol, timeframe="1m", limit=1)
                last_close = ticker_ohlcv[-1][4]
            except Exception as exc:
                if base_free > 0:
                    lines.append(
                        f"- {symbol}: {format_number(base_free, 8)} {base} | 현재가 조회 실패"
                    )
                lines.append(
                    format_exchange_error_text("UPBIT", "현재가 조회", exc, symbol=symbol)
                )
                continue

            estimated_value = base_free * last_close
            if estimated_value >= 100:
                meaningful_position_count += 1
                line = (
                    f"- {symbol}: {format_number(base_free, 8)} {base} | "
                    f"현재가 {format_number(last_close, 0)} | "
                    f"평가 {format_number(estimated_value, 0)} {quote}"
                )
                entry_price = recovered_entry_prices.get(symbol)
                if entry_price is None:
                    entry_price = latest_entry_prices.get(("UPBIT", symbol))
                if entry_price and entry_price > 0:
                    pnl_pct = ((last_close - entry_price) / entry_price) * 100
                    line += (
                        f" | 진입가 {format_number(entry_price, 0)} | "
                        f"현재 손익 {format_pnl_badge(pnl_pct)}"
                    )
                lines.append(line)

        if meaningful_position_count == 0:
            lines.append("- 의미 있는 코인 보유 포지션 없음")
        return "\n".join(lines)
    except Exception as exc:
        return "[UPBIT]\n" + format_exchange_error_text("UPBIT", "초기화", exc)


def build_pnl_text() -> str:
    """오늘 체결 이력 기준 KRW, USDT 누적 손익 요약을 만든다."""
    trade_paths = iter_files("trade_logs", "trade_history.jsonl")
    if not trade_paths:
        return "오늘 누적 실현 손익\n- 체결 이력이 아직 없습니다."

    today_prefix = datetime.now().strftime("%Y-%m-%d")
    totals: dict[str, float] = {}
    trade_counts: dict[str, int] = {}
    estimated_counts: dict[str, int] = {}
    gross_fallback_counts: dict[str, int] = {}

    for path in trade_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                continue

            recorded_local = str(record.get("recorded_at_local", ""))
            if not recorded_local.startswith(today_prefix):
                continue
            if str(record.get("side", "")).lower() != "sell":
                continue

            quote = str(record.get("quote_currency", "")).strip().upper()
            if not quote:
                continue

            net_value = record.get("net_realized_pnl_quote")
            gross_value = record.get("realized_pnl_quote")
            used_estimated_net = False
            used_gross_fallback = False
            exchange_name = str(record.get("exchange", "")).strip().upper()

            try:
                if net_value not in (None, ""):
                    pnl_value = float(net_value)
                    if exchange_name == "OKX":
                        okx_fee_rate_pct = os.getenv("OKX_FEE_RATE_PCT", "0.1")
                        estimated_fee, estimated_net, _ = estimate_round_trip_net_pnl(
                            entry_price=record.get("estimated_entry_price"),
                            exit_price=record.get("reference_price"),
                            amount=record.get("amount"),
                            fee_rate_pct=okx_fee_rate_pct,
                            realized_pnl_quote=gross_value,
                        )
                        if estimated_fee is not None and estimated_net is not None:
                            pnl_value = float(estimated_net)
                            used_estimated_net = True
                elif gross_value not in (None, ""):
                    fee_rate_pct = record.get("fee_rate_pct")
                    if fee_rate_pct in (None, ""):
                        if exchange_name == "UPBIT":
                            fee_rate_pct = os.getenv("UPBIT_FEE_RATE_PCT", "0.05")
                        elif exchange_name == "OKX":
                            fee_rate_pct = os.getenv("OKX_FEE_RATE_PCT", "0.1")

                    estimated_fee, estimated_net, _ = estimate_round_trip_net_pnl(
                        entry_price=record.get("estimated_entry_price"),
                        exit_price=record.get("reference_price"),
                        amount=record.get("amount"),
                        fee_rate_pct=fee_rate_pct,
                        realized_pnl_quote=gross_value,
                    )
                    if estimated_fee is not None and estimated_net is not None:
                        pnl_value = float(estimated_net)
                        used_estimated_net = True
                    else:
                        pnl_value = float(gross_value)
                        used_gross_fallback = True
                else:
                    continue
            except (TypeError, ValueError):
                continue

            totals[quote] = totals.get(quote, 0.0) + pnl_value
            trade_counts[quote] = trade_counts.get(quote, 0) + 1
            if used_estimated_net:
                estimated_counts[quote] = estimated_counts.get(quote, 0) + 1
            if used_gross_fallback:
                gross_fallback_counts[quote] = gross_fallback_counts.get(quote, 0) + 1

    if not totals:
        return "오늘 누적 실현 손익\n- 오늘 집계된 실현 손익 체결이 아직 없습니다."

    lines = ["오늘 누적 실현 손익"]
    for quote in sorted(totals):
        decimals = 0 if quote == "KRW" else 4
        label = "원화 손익" if quote == "KRW" else f"{quote} 손익"
        unit = "원" if quote == "KRW" else f" {quote}"
        value_text = (
            format_number_trunc(totals[quote], decimals)
            if quote == "KRW"
            else format_number(totals[quote], decimals)
        )
        lines.append(
            f"- {label}: {value_text}{unit} "
            f"(체결 {trade_counts.get(quote, 0)}건)"
        )
        estimated_count = estimated_counts.get(quote, 0)
        if estimated_count:
            lines.append(
                f"  참고: {estimated_count}건은 왕복 수수료를 반영한 순손익 기준입니다."
            )
        gross_fallback_count = gross_fallback_counts.get(quote, 0)
        if gross_fallback_count:
            lines.append(
                f"  참고: {gross_fallback_count}건은 순손익 추정 정보가 부족해 실현 손익 기준으로 합산했습니다."
            )
    return "\n".join(lines)


def build_period_pnl_text(days: int, *, title: str) -> str:
    """최근 N일 기준 누적 실현 손익 요약을 만든다."""
    trade_paths = iter_files("trade_logs", "trade_history.jsonl")
    if not trade_paths:
        return f"{title}\n- 체결 이력이 아직 없습니다."

    now = datetime.now()
    totals: dict[str, float] = {}
    trade_counts: dict[str, int] = {}
    estimated_counts: dict[str, int] = {}
    gross_fallback_counts: dict[str, int] = {}

    for path in trade_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                continue

            recorded_local = str(record.get("recorded_at_local", ""))
            if not is_in_recent_days(recorded_local, days, now=now):
                continue
            if str(record.get("side", "")).lower() != "sell":
                continue

            quote = str(record.get("quote_currency", "")).strip().upper()
            if not quote:
                continue

            net_value = record.get("net_realized_pnl_quote")
            gross_value = record.get("realized_pnl_quote")
            used_estimated_net = False
            used_gross_fallback = False
            exchange_name = str(record.get("exchange", "")).strip().upper()

            try:
                if net_value not in (None, ""):
                    pnl_value = float(net_value)
                    if exchange_name == "OKX":
                        okx_fee_rate_pct = os.getenv("OKX_FEE_RATE_PCT", "0.1")
                        estimated_fee, estimated_net, _ = estimate_round_trip_net_pnl(
                            entry_price=record.get("estimated_entry_price"),
                            exit_price=record.get("reference_price"),
                            amount=record.get("amount"),
                            fee_rate_pct=okx_fee_rate_pct,
                            realized_pnl_quote=gross_value,
                        )
                        if estimated_fee is not None and estimated_net is not None:
                            pnl_value = float(estimated_net)
                            used_estimated_net = True
                elif gross_value not in (None, ""):
                    fee_rate_pct = record.get("fee_rate_pct")
                    if fee_rate_pct in (None, ""):
                        if exchange_name == "UPBIT":
                            fee_rate_pct = os.getenv("UPBIT_FEE_RATE_PCT", "0.05")
                        elif exchange_name == "OKX":
                            fee_rate_pct = os.getenv("OKX_FEE_RATE_PCT", "0.1")

                    estimated_fee, estimated_net, _ = estimate_round_trip_net_pnl(
                        entry_price=record.get("estimated_entry_price"),
                        exit_price=record.get("reference_price"),
                        amount=record.get("amount"),
                        fee_rate_pct=fee_rate_pct,
                        realized_pnl_quote=gross_value,
                    )
                    if estimated_fee is not None and estimated_net is not None:
                        pnl_value = float(estimated_net)
                        used_estimated_net = True
                    else:
                        pnl_value = float(gross_value)
                        used_gross_fallback = True
                else:
                    continue
            except (TypeError, ValueError):
                continue

            totals[quote] = totals.get(quote, 0.0) + pnl_value
            trade_counts[quote] = trade_counts.get(quote, 0) + 1
            if used_estimated_net:
                estimated_counts[quote] = estimated_counts.get(quote, 0) + 1
            if used_gross_fallback:
                gross_fallback_counts[quote] = gross_fallback_counts.get(quote, 0) + 1

    if not totals:
        return f"{title}\n- 최근 {days}일 기준 실현 손익 체결이 아직 없습니다."

    lines = [title]
    for quote in sorted(totals):
        decimals = 0 if quote == "KRW" else 4
        label = "원화 손익" if quote == "KRW" else f"{quote} 손익"
        unit = "원" if quote == "KRW" else f" {quote}"
        value_text = (
            format_number_trunc(totals[quote], decimals)
            if quote == "KRW"
            else format_number(totals[quote], decimals)
        )
        lines.append(
            f"- {label}: {value_text}{unit} "
            f"(체결 {trade_counts.get(quote, 0)}건)"
        )
        estimated_count = estimated_counts.get(quote, 0)
        if estimated_count:
            lines.append(
                f"  참고: {estimated_count}건은 왕복 수수료를 반영한 순손익 기준입니다."
            )
        gross_fallback_count = gross_fallback_counts.get(quote, 0)
        if gross_fallback_count:
            lines.append(
                f"  참고: {gross_fallback_count}건은 순손익 추정 정보가 부족해 실현 손익 기준으로 합산했습니다."
            )
    return "\n".join(lines)


def build_analysis_text(settings: ListenerSettings) -> str:
    """시장 로그 분석과 전략 퍼널 분석을 함께 요약한 문구를 만든다."""
    sections = [
        build_market_analysis_text(settings),
        build_current_market_strategy_text(settings),
        build_recovered_position_state_text(settings),
        build_backtest_comparison_text(settings),
        build_strategy_funnel_text(),
        build_trade_quality_text(settings),
        build_profit_protect_text(),
        build_filter_gap_text(),
        build_time_of_day_text(),
        build_volume_candidate_text(settings),
    ]
    return "\n\n".join(section for section in sections if section)


def iter_recent_trade_records(days: int) -> list[dict]:
    """최근 N일 기준 체결 이력 레코드를 반환한다."""
    now = datetime.now()
    rows: list[dict] = []
    for path in iter_files("trade_logs", "trade_history.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                continue
            if is_in_recent_days(str(record.get("recorded_at_local", "")), days, now=now):
                rows.append(record)
    return rows


def build_weekly_trade_quality_text(days: int = 7, limit: int = 8) -> str:
    """최근 N일 기준 체결 품질 요약을 만든다."""
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    grouped_execution: dict[tuple[str, str, str], list[dict]] = {}
    for record in iter_recent_trade_records(days):
        key = (
            str(record.get("program_name", "")),
            str(record.get("symbol", "")),
            str(record.get("quote_currency", "")),
        )
        grouped_execution.setdefault(key, []).append(record)
        if record.get("side") != "sell":
            continue
        grouped.setdefault(key, []).append(record)

    if not grouped:
        return f"최근 {days}일 거래 품질 요약\n- 아직 최근 {days}일 체결 데이터가 없습니다."

    lines = [f"최근 {days}일 거래 품질 요약"]
    sorted_groups = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
    )
    for (program_name, symbol, quote_currency), records in sorted_groups[:limit]:
        execution_records = grouped_execution.get((program_name, symbol, quote_currency), [])
        pnl_values: list[float] = []
        mfe_values: list[float] = []
        mae_values: list[float] = []
        api_latency_values: list[float] = []
        slippage_values: list[float] = []
        fill_ratio_values: list[float] = []
        win_count = 0
        exit_reasons: dict[str, int] = {}
        net_quote_total = 0.0

        for record in records:
            pnl_value = safe_float(record.get("net_realized_pnl_pct"))
            if pnl_value is None:
                pnl_value = safe_float(record.get("realized_pnl_pct"))
            if pnl_value is not None:
                pnl_values.append(pnl_value)
                if pnl_value > 0:
                    win_count += 1

            mfe_value = safe_float(record.get("mfe_pct"))
            if mfe_value is not None:
                mfe_values.append(mfe_value)

            mae_value = safe_float(record.get("mae_pct"))
            if mae_value is not None:
                mae_values.append(mae_value)

            net_quote = safe_float(record.get("net_realized_pnl_quote"))
            if net_quote is None:
                net_quote = safe_float(record.get("realized_pnl_quote"))
            if net_quote is not None:
                net_quote_total += net_quote

            reason = str(record.get("reason", "")).strip() or "-"
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        for record in execution_records:
            api_latency = safe_float(record.get("api_latency_ms"))
            if api_latency is not None:
                api_latency_values.append(api_latency)

            slippage_bps = safe_float(record.get("slippage_bps"))
            if slippage_bps is not None:
                slippage_values.append(slippage_bps)

            fill_ratio = safe_float(record.get("fill_ratio"))
            if fill_ratio is not None:
                fill_ratio_values.append(fill_ratio * 100)

        avg_pnl = f"{(sum(pnl_values) / len(pnl_values)):.3f}" if pnl_values else "-"
        avg_mfe = f"{(sum(mfe_values) / len(mfe_values)):.3f}" if mfe_values else "-"
        avg_mae = f"{(sum(mae_values) / len(mae_values)):.3f}" if mae_values else "-"
        avg_api_latency = (
            f"{(sum(api_latency_values) / len(api_latency_values)):.1f}"
            if api_latency_values
            else "-"
        )
        avg_slippage = (
            f"{(sum(slippage_values) / len(slippage_values)):.2f}"
            if slippage_values
            else "-"
        )
        avg_fill_ratio = (
            f"{(sum(fill_ratio_values) / len(fill_ratio_values)):.1f}"
            if fill_ratio_values
            else "-"
        )
        win_rate = f"{(win_count / len(records)) * 100:.1f}%" if records else "-"
        top_exit_reason = sorted(exit_reasons.items(), key=lambda item: (-item[1], item[0]))[0][0]
        decimals = 0 if quote_currency == "KRW" else 4
        lines.append(
            f"- {program_name} | {symbol} | 거래 {len(records)}건 | 승률 {win_rate} | "
            f"평균 손익 {avg_pnl}% | 총 순손익 {format_number(net_quote_total, decimals)} {quote_currency} | "
            f"MFE {avg_mfe}% / MAE {avg_mae}% | "
            f"API {avg_api_latency}ms | 슬리피지 {avg_slippage}bp | 체결비율 {avg_fill_ratio}% | "
            f"대표 청산 {top_exit_reason}"
        )
    return "\n".join(lines)


def _build_profit_protect_section(records: list[dict], title: str, limit: int = 6) -> str:
    """순익 보호 익절 체결 요약 문구를 만든다."""
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for record in records:
        if record.get("side") != "sell":
            continue
        if str(record.get("reason", "")).strip() != "profit_protect_take_profit":
            continue
        key = (
            str(record.get("program_name", "")),
            str(record.get("symbol", "")),
            str(record.get("quote_currency", "")),
        )
        grouped.setdefault(key, []).append(record)

    if not grouped:
        return f"{title}\n- 아직 순익 보호 익절 체결이 없습니다."

    lines = [title]
    rows = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
    )
    for (program_name, symbol, quote_currency), items in rows[:limit]:
        net_pnl_values: list[float] = []
        net_quote_total = 0.0
        for record in items:
            net_pct = safe_float(record.get("net_realized_pnl_pct"))
            if net_pct is None:
                net_pct = safe_float(record.get("realized_pnl_pct"))
            if net_pct is not None:
                net_pnl_values.append(net_pct)

            net_quote = safe_float(record.get("net_realized_pnl_quote"))
            if net_quote is None:
                net_quote = safe_float(record.get("realized_pnl_quote"))
            if net_quote is not None:
                net_quote_total += net_quote

        avg_net_pnl = (
            f"{(sum(net_pnl_values) / len(net_pnl_values)):.3f}"
            if net_pnl_values
            else "-"
        )
        decimals = 0 if quote_currency == "KRW" else 4
        lines.append(
            f"- {program_name} | {symbol} | {len(items)}건 | "
            f"평균 순손익 {avg_net_pnl}% | "
            f"총 순손익 {format_number(net_quote_total, decimals)} {quote_currency}"
        )
    return "\n".join(lines)


def build_profit_protect_text(limit: int = 6) -> str:
    """전체 누적 기준 순익 보호 익절 요약을 만든다."""
    records: list[dict] = []
    for path in iter_files("trade_logs", "trade_history.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except (ValueError, json.JSONDecodeError):
                continue
    return _build_profit_protect_section(records, "순익 보호 익절 요약", limit=limit)


def build_weekly_profit_protect_text(days: int = 7, limit: int = 6) -> str:
    """최근 N일 기준 순익 보호 익절 요약을 만든다."""
    return _build_profit_protect_section(
        iter_recent_trade_records(days),
        f"최근 {days}일 순익 보호 익절 요약",
        limit=limit,
    )


def build_weekly_funnel_text(days: int = 7, limit: int = 8) -> str:
    """최근 N일 기준 전략 퍼널 요약을 만든다."""
    base_dir = Path("structured_logs/live")
    if not base_dir.exists():
        return f"최근 {days}일 전략 퍼널 요약\n- 구조화 전략 로그가 아직 없습니다."

    now = datetime.now()
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    for program_name in analyze_strategy_logs.find_program_names(base_dir):
        for record in analyze_strategy_logs.read_program_records(base_dir, program_name, "strategy.jsonl"):
            if not is_in_recent_days(str(record.get("recorded_at_local", "")), days, now=now):
                continue
            key = (program_name, str(record.get("symbol", "")), str(record.get("side", "")))
            bucket = grouped.setdefault(
                key,
                {
                    "scans": 0,
                    "ready": 0,
                    "filled": 0,
                    "block_reasons": {},
                },
            )
            if record.get("stage") == "scan" and record.get("result") == "seen":
                bucket["scans"] = int(bucket["scans"]) + 1
            if record.get("result") == "ready" and record.get("stage") in {"buy_ready", "sell_ready"}:
                bucket["ready"] = int(bucket["ready"]) + 1
            if record.get("stage") == "filled" and record.get("result") == "filled":
                bucket["filled"] = int(bucket["filled"]) + 1
            if record.get("result") == "blocked":
                reason = str(record.get("reason", "")).strip() or "-"
                block_reasons = bucket["block_reasons"]
                if isinstance(block_reasons, dict):
                    block_reasons[reason] = int(block_reasons.get(reason, 0)) + 1

    if not grouped:
        return f"최근 {days}일 전략 퍼널 요약\n- 아직 최근 {days}일 전략 로그가 없습니다."

    lines = [f"최근 {days}일 전략 퍼널 요약"]
    rows = sorted(
        grouped.items(),
        key=lambda item: (-int(item[1]["scans"]), item[0][0], item[0][1], item[0][2]),
    )
    for (program_name, symbol, side), bucket in rows[:limit]:
        block_reasons = bucket["block_reasons"] if isinstance(bucket["block_reasons"], dict) else {}
        top_block_reason = "-"
        if block_reasons:
            top_block_reason = sorted(block_reasons.items(), key=lambda item: (-item[1], item[0]))[0][0]
        lines.append(
            f"- {program_name} | {symbol} {side} | "
            f"scan {bucket['scans']} -> ready {bucket['ready']} -> filled {bucket['filled']} | "
            f"주요 병목 {top_block_reason}"
        )
    return "\n".join(lines)


def build_weekly_time_of_day_text(days: int = 7, limit: int = 6) -> str:
    """최근 N일 기준 시간대 성과 요약을 만든다."""
    grouped: dict[int, list[float]] = {}
    for record in iter_recent_trade_records(days):
        if record.get("side") != "sell":
            continue
        parsed = parse_local_timestamp(str(record.get("recorded_at_local", "")))
        if parsed is None:
            continue
        pnl_value = safe_float(record.get("net_realized_pnl_pct"))
        if pnl_value is None:
            pnl_value = safe_float(record.get("realized_pnl_pct"))
        if pnl_value is None:
            continue
        grouped.setdefault(parsed.hour, []).append(pnl_value)

    if not grouped:
        return f"최근 {days}일 시간대 성과 요약\n- 아직 최근 {days}일 시간대별 체결 데이터가 없습니다."

    rows = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    lines = [f"최근 {days}일 시간대 성과 요약"]
    for hour, values in rows[:limit]:
        avg_pnl = sum(values) / len(values)
        lines.append(
            f"- {hour:02d}시 | 거래 {len(values)}건 | 평균 손익 {avg_pnl:.3f}%"
        )
    return "\n".join(lines)


def build_weekly_report_text(settings: ListenerSettings) -> str:
    """최근 7일 기준 주간 리포트 문구를 만든다."""
    now = datetime.now()
    start = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    end = now.strftime("%Y-%m-%d %H:%M:%S")
    return "\n\n".join(
        [
            "주간 리포트",
            f"집계 구간: {start} ~ {end}",
            build_period_pnl_text(7, title="최근 7일 누적 실현 손익"),
            build_positions_text(settings),
            build_current_market_strategy_text(settings),
            build_backtest_comparison_text(settings),
            build_weekly_trade_quality_text(7),
            build_weekly_profit_protect_text(7),
            build_weekly_funnel_text(7),
            build_weekly_time_of_day_text(7),
            build_volume_candidate_text(settings),
        ]
    )


def build_market_analysis_text(settings: ListenerSettings) -> str:
    """시장 분석 수집 로그 요약 문구를 만든다."""
    records = analyze_logs.load_records(settings.analysis_log_dir)
    summaries = analyze_logs.build_summaries(records)
    managed_symbols = set(settings.okx_symbols + settings.upbit_symbols)
    summaries = [item for item in summaries if item.symbol in managed_symbols]
    if not summaries:
        return "분석 로그가 아직 없습니다. analysis_log_collector.py 가 더 수집한 뒤 다시 확인해 주세요."

    lines = ["시장 로그 분석 요약"]
    for item in summaries:
        lines.append(
            f"- {item.exchange.upper()} {item.symbol} | "
            f"수집 {item.count}건 | "
            f"평균 이격도 {item.avg_gap_pct:.4f}% | "
            f"평균 절대 변화율 {item.avg_abs_change_pct:.4f}% | "
            f"매수 {item.bullish_count}회 / 매도 {item.bearish_count}회"
        )
    return "\n".join(lines)


def load_latest_market_records(settings: ListenerSettings) -> list[dict]:
    """심볼별 최신 분석 로그 1건씩을 반환한다."""
    records = analyze_logs.load_records(settings.analysis_log_dir)
    latest_by_key: dict[tuple[str, str], tuple[datetime, dict]] = {}

    for record in records:
        exchange = str(record.get("exchange", "")).strip()
        symbol = str(record.get("symbol", "")).strip()
        collected_at = parse_local_timestamp(str(record.get("collected_at", "")))
        if not exchange or not symbol or collected_at is None:
            continue
        key = (exchange, symbol)
        current = latest_by_key.get(key)
        if current is None or collected_at > current[0]:
            latest_by_key[key] = (collected_at, record)

    managed_symbols = set(settings.okx_symbols + settings.upbit_symbols)
    rows = [item[1] for item in latest_by_key.values() if str(item[1].get("symbol", "")) in managed_symbols]
    rows.sort(key=lambda row: (str(row.get("exchange", "")), str(row.get("symbol", ""))))
    return rows


def build_current_market_strategy_text(settings: ListenerSettings) -> str:
    """최신 시장 상태와 현재 로그 기준 전략 추천 문구를 만든다."""
    latest_rows = load_latest_market_records(settings)
    if not latest_rows:
        return "현재 시장 해석과 전략 추천\n- 최신 분석 로그가 아직 없어 현재 시장 해석을 만들 수 없습니다."

    bullish_count = sum(1 for row in latest_rows if row.get("bullish_signal"))
    bearish_count = sum(1 for row in latest_rows if row.get("bearish_signal"))
    above_ma_count = sum(1 for row in latest_rows if row.get("above_ma"))
    ready_count = sum(1 for row in latest_rows if row.get("public_buy_ready"))

    volume_values = [
        value
        for value in (safe_float(row.get("volume_ratio")) for row in latest_rows)
        if value is not None
    ]
    volatility_values = [
        value
        for value in (safe_float(row.get("avg_abs_change_pct")) for row in latest_rows)
        if value is not None
    ]
    spread_values = [
        value
        for value in (safe_float(row.get("spread_pct")) for row in latest_rows)
        if value is not None
    ]

    avg_volume_ratio = sum(volume_values) / len(volume_values) if volume_values else 0.0
    avg_abs_change_pct = (
        sum(volatility_values) / len(volatility_values) if volatility_values else 0.0
    )
    avg_spread_pct = sum(spread_values) / len(spread_values) if spread_values else 0.0

    scored_rows: list[tuple[float, str]] = []
    for row in latest_rows:
        symbol = str(row.get("symbol", "")).strip()
        score = 0.0
        if row.get("bullish_signal"):
            score += 1.0
        if row.get("above_ma"):
            score += 0.8
        if row.get("public_buy_ready"):
            score += 1.2
        score += min(safe_float(row.get("volume_ratio")) or 0.0, 3.0) * 0.3
        score += min(safe_float(row.get("avg_abs_change_pct")) or 0.0, 1.0) * 2.0
        scored_rows.append((score, symbol))

    leaders = [symbol for _, symbol in sorted(scored_rows, reverse=True)[:3] if symbol]
    laggards = [symbol for _, symbol in sorted(scored_rows)[:3] if symbol]

    lines = ["현재 시장 해석과 전략 추천"]
    lines.append(
        f"- 최신 심볼 {len(latest_rows)}개 | 상승 신호 {bullish_count}개 | 하락 신호 {bearish_count}개 | "
        f"MA 위 {above_ma_count}개 | 공개 기준 매수 준비 {ready_count}개"
    )
    lines.append(
        f"- 평균 거래량 배수 {avg_volume_ratio:.3f}배 | "
        f"평균 절대 변화율 {avg_abs_change_pct:.4f}% | "
        f"평균 스프레드 {avg_spread_pct:.4f}%"
    )
    if leaders:
        lines.append(f"- 상대 강세 후보: {', '.join(leaders)}")
    if laggards:
        lines.append(f"- 상대 약세/혼조 후보: {', '.join(laggards)}")

    if avg_volume_ratio < 0.90 and avg_abs_change_pct < 0.10:
        lines.append(
            "- 추천: 시장 에너지가 약하니 단타는 강한 신호만 선별하고, 보유 중 포지션은 순익 보호/브레이크이븐 중심이 더 맞습니다."
        )
    elif bearish_count > bullish_count and ready_count == 0:
        lines.append(
            "- 추천: 약세 우위라 신규 추격 매수보다 손절 우선, 순익 보호, 관망 비중 확대가 더 안전합니다."
        )
    elif bullish_count >= bearish_count and avg_volume_ratio >= 1.00:
        lines.append(
            "- 추천: 상승 추세 확인형 전략이 비교적 맞습니다. BTC/ETH 중심 추세추종은 유지하고, 알트는 거래량 동반 구간만 받는 편이 좋습니다."
        )
    else:
        lines.append(
            "- 추천: 방향성이 혼재해 보수형 단타가 적합합니다. BTC/USDT는 강화된 진입 필터 유지, ETH/KRW는 브레이크이븐 가드 우선이 맞습니다."
        )

    return "\n".join(lines)


def build_regime_text(settings: ListenerSettings) -> str:
    """심볼별 현재 레짐과 핵심 근거 숫자를 요약한다."""
    latest_rows = load_latest_market_records(settings)
    if not latest_rows:
        return "현재 레짐 요약\n- 최신 분석 로그가 아직 없어 레짐을 계산할 수 없습니다."

    lines = ["현재 레짐 요약"]
    for row in latest_rows:
        exchange = str(row.get("exchange", "")).upper()
        symbol = str(row.get("symbol", ""))
        snapshot = classify_symbol_regime(row)
        volume_ratio = "-" if snapshot.volume_ratio is None else f"{snapshot.volume_ratio:.3f}"
        abs_change = (
            "-"
            if snapshot.avg_abs_change_pct is None
            else f"{snapshot.avg_abs_change_pct:.4f}%"
        )
        gap_pct = "-" if snapshot.gap_pct is None else f"{snapshot.gap_pct:.4f}%"
        rsi_text = "-" if snapshot.rsi is None else f"{snapshot.rsi:.1f}"
        ready_text = "Y" if snapshot.public_buy_ready else "N"
        lines.append(
            f"- {exchange} {symbol} | {snapshot.regime} | "
            f"거래량 {volume_ratio}배 | 변화율 {abs_change} | "
            f"이격도 {gap_pct} | RSI {rsi_text} | 준비 {ready_text}"
        )
    return "\n".join(lines)


def fetch_public_json(url: str, timeout: int = 20) -> object:
    """공개 HTTP JSON 응답을 읽는다."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_volume_candidate_text(settings: ListenerSettings) -> str:
    """최근 1주 거래량 기준 신규 분석 후보 코인을 거래소별로 요약한다."""
    lines = ["거래량 기준 신규 후보 코인"]

    okx_candidates, okx_error = fetch_okx_volume_candidates(settings.okx_symbols)
    if okx_error:
        lines.append(f"- OKX: 후보 조회 실패 ({okx_error})")
    elif not okx_candidates:
        lines.append("- OKX: 새로 추가할 만한 상위 후보가 아직 없습니다.")
    else:
        okx_text = ", ".join(
            f"{symbol} ({format_number(week_quote, 0)} USDT)"
            for symbol, week_quote in okx_candidates
        )
        lines.append(f"- OKX: {okx_text}")

    upbit_candidates, upbit_error = fetch_upbit_volume_candidates(settings.upbit_symbols)
    if upbit_error:
        lines.append(f"- UPBIT: 후보 조회 실패 ({upbit_error})")
    elif not upbit_candidates:
        lines.append("- UPBIT: 새로 추가할 만한 상위 후보가 아직 없습니다.")
    else:
        upbit_text = ", ".join(
            f"{symbol} ({format_number(week_quote, 0)} KRW)"
            for symbol, week_quote in upbit_candidates
        )
        lines.append(f"- UPBIT: {upbit_text}")

    return "\n".join(lines)


def fetch_okx_volume_candidates(
    managed_symbols: list[str],
    *,
    limit: int = VOLUME_CANDIDATE_COUNT,
) -> tuple[list[tuple[str, float]], str | None]:
    """OKX 에서 최근 1주 거래량 기준 신규 후보를 추린다."""
    try:
        payload = fetch_public_json(OKX_TICKERS_URL)
        data = payload.get("data", []) if isinstance(payload, dict) else []
        candidates: list[tuple[str, float]] = []
        for row in data:
            inst_id = str(row.get("instId", "")).strip()
            if not inst_id.endswith("-USDT"):
                continue
            try:
                vol_quote = float(row.get("volCcy24h") or 0.0)
            except (TypeError, ValueError):
                vol_quote = 0.0
            candidates.append((inst_id, vol_quote))

        candidates.sort(key=lambda item: item[1], reverse=True)
        weekly_rows: list[tuple[str, float]] = []
        for inst_id, _ in candidates[:30]:
            time.sleep(0.08)
            encoded = urllib.parse.quote(inst_id, safe="")
            candle_payload = fetch_public_json(OKX_CANDLES_URL.format(inst=encoded))
            candle_rows = (
                candle_payload.get("data", [])
                if isinstance(candle_payload, dict)
                else []
            )
            week_quote = 0.0
            for item in candle_rows:
                try:
                    week_quote += float(item[7])
                except (TypeError, ValueError, IndexError):
                    continue
            symbol = inst_id.replace("-", "/")
            weekly_rows.append((symbol, week_quote))

        return filter_new_volume_candidates(weekly_rows, managed_symbols, limit), None
    except Exception as exc:
        return [], format_telegram_request_error(exc)


def fetch_upbit_volume_candidates(
    managed_symbols: list[str],
    *,
    limit: int = VOLUME_CANDIDATE_COUNT,
) -> tuple[list[tuple[str, float]], str | None]:
    """업비트에서 최근 1주 거래량 기준 신규 후보를 추린다."""
    try:
        payload = fetch_public_json(UPBIT_TICKER_ALL_URL)
        rows = payload if isinstance(payload, list) else []
        candidates: list[tuple[str, float]] = []
        for row in rows:
            market = str(row.get("market", "")).strip()
            if not market.startswith("KRW-"):
                continue
            try:
                trade_price = float(row.get("acc_trade_price_24h") or 0.0)
            except (TypeError, ValueError):
                trade_price = 0.0
            candidates.append((market, trade_price))

        candidates.sort(key=lambda item: item[1], reverse=True)
        weekly_rows: list[tuple[str, float]] = []
        for market, _ in candidates[:20]:
            time.sleep(0.12)
            encoded = urllib.parse.quote(market, safe="")
            candle_rows = fetch_public_json(UPBIT_CANDLES_URL.format(market=encoded))
            week_quote = 0.0
            for item in candle_rows if isinstance(candle_rows, list) else []:
                try:
                    week_quote += float(item.get("candle_acc_trade_price") or 0.0)
                except (TypeError, ValueError):
                    continue
            symbol = market.replace("KRW-", "") + "/KRW"
            weekly_rows.append((symbol, week_quote))

        return filter_new_volume_candidates(weekly_rows, managed_symbols, limit), None
    except Exception as exc:
        return [], format_telegram_request_error(exc)


def filter_new_volume_candidates(
    rows: list[tuple[str, float]],
    managed_symbols: list[str],
    limit: int,
) -> list[tuple[str, float]]:
    """이미 관리 중인 심볼과 스테이블 자산을 제외하고 상위 후보를 추린다."""
    managed = set(managed_symbols)
    filtered: list[tuple[str, float]] = []
    for symbol, week_quote in sorted(rows, key=lambda item: item[1], reverse=True):
        base = symbol.split("/", 1)[0]
        if symbol in managed:
            continue
        if base in STABLE_BASES:
            continue
        filtered.append((symbol, week_quote))
        if len(filtered) >= limit:
            break
    return filtered


def build_strategy_funnel_text(limit: int = 8) -> str:
    """구조화 전략 로그 퍼널 요약 문구를 만든다."""
    base_dir = Path("structured_logs/live")
    if not base_dir.exists():
        return "전략 퍼널 분석 요약\n- 구조화 전략 로그가 아직 없습니다. 봇을 재시작해 새 strategy.jsonl 이 쌓인 뒤 다시 확인해 주세요."

    rows = analyze_strategy_logs.build_summary_rows(base_dir)
    if not rows:
        return "전략 퍼널 분석 요약\n- 아직 집계할 전략 퍼널 로그가 없습니다."

    def sort_key(row: dict) -> tuple:
        return (row.get("program_name", ""), row.get("symbol", ""), row.get("side", ""))

    lines = ["전략 퍼널 분석 요약"]
    for row in sorted(rows, key=sort_key)[:limit]:
        lines.append(
            f"- {row['program_name']} | {row['symbol']} {row['side']} | "
            f"scan {row['scans']} -> ready {row['ready']} -> filled {row['filled']} | "
            f"주요 병목 {row['top_block_reason']}"
        )
    return "\n".join(lines)


def format_metric_with_unit(value: str, unit: str) -> str:
    """지표 문자열이 비어 있지 않을 때만 단위를 붙인다."""
    normalized = str(value).strip()
    if not normalized or normalized == "-":
        return "-"
    return f"{normalized}{unit}"


def build_trade_quality_text(settings: ListenerSettings | None = None, limit: int = 8) -> str:
    """체결 품질 요약 문구를 만든다."""
    rows = analyze_strategy_logs.build_trade_quality_rows()
    if settings is not None:
        managed_symbols = set(settings.okx_symbols + settings.upbit_symbols)
        rows = [row for row in rows if str(row.get("symbol", "")) in managed_symbols]
    if not rows:
        return "거래 품질 요약\n- 아직 집계할 체결 품질 로그가 없습니다."

    lines = ["거래 품질 요약"]
    for row in rows[:limit]:
        lines.append(
            f"- {row['program_name']} | {row['symbol']} | "
            f"거래 {row['trades']}건 | "
            f"평균 손익 {row['avg_net_pnl_pct']}% | "
            f"MFE {row['avg_mfe_pct']}% / MAE {row['avg_mae_pct']}% | "
            f"보유 {format_metric_with_unit(row['avg_holding_seconds'], '초')} | "
            f"트레일링 활성 {row['trailing_arm_rate']} | "
            f"API {format_metric_with_unit(row['avg_api_latency_ms'], 'ms')} | "
            f"슬리피지 {format_metric_with_unit(row['avg_slippage_bps'], 'bp')} | "
            f"체결비율 {format_metric_with_unit(row['avg_fill_ratio_pct'], '%')}"
        )
    return "\n".join(lines)


def build_filter_gap_text(limit: int = 8) -> str:
    """필터 기준 부족 폭 요약 문구를 만든다."""
    base_dir = Path("structured_logs/live")
    if not base_dir.exists():
        return "필터 기준 부족 폭 요약\n- 구조화 전략 로그가 아직 없습니다."

    rows = analyze_strategy_logs.build_filter_gap_rows(base_dir)
    if not rows:
        return "필터 기준 부족 폭 요약\n- 아직 집계할 기준 부족 로그가 없습니다."

    rows = sorted(rows, key=lambda item: (-int(item["count"]), item["program_name"], item["symbol"]))
    lines = ["필터 기준 부족 폭 요약"]
    for row in rows[:limit]:
        lines.append(
            f"- {row['program_name']} | {row['symbol']} | {row['reason']} | "
            f"{row['count']}회 | 평균 부족 {row['avg_shortfall']} | 최대 부족 {row['max_shortfall']}"
        )
    return "\n".join(lines)


def build_time_of_day_text(limit: int = 6) -> str:
    """시간대 성과 요약 문구를 만든다."""
    rows = analyze_strategy_logs.build_time_of_day_rows()
    if not rows:
        return "시간대 성과 요약\n- 아직 시간대별 체결 데이터가 없습니다."

    rows = sorted(rows, key=lambda item: (-int(item["trades"]), int(item["hour"])))
    lines = ["시간대 성과 요약"]
    for row in rows[:limit]:
        lines.append(
            f"- {int(row['hour']):02d}시 | 거래 {row['trades']}건 | 평균 손익 {row['avg_net_pnl_pct']}%"
        )
    return "\n".join(lines)


def load_latest_summary_pairs() -> dict[tuple[str, str], list[dict]]:
    """프로그램/심볼별 최신 2개 시간 버킷 요약을 읽는다."""
    base_dir = Path("structured_logs/live")
    pairs: dict[tuple[str, str], list[dict]] = {}
    if not base_dir.exists():
        return pairs

    grouped: dict[tuple[str, str], list[dict]] = {}
    for path in iter_files(base_dir, "*.json"):
        if "summary_1h" not in path.parts:
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        program_name = path.parent.parent.name
        key = (program_name, str(record.get("symbol", "")))
        grouped.setdefault(key, []).append(record)

    for key, records in grouped.items():
        records.sort(key=lambda item: str(item.get("time_bucket", "")), reverse=True)
        pairs[key] = records[:2]
    return pairs


def build_bottleneck_change_text(limit: int = 8) -> str:
    """최근 시간 버킷 기준 주요 병목 변화 요약을 만든다."""
    pairs = load_latest_summary_pairs()
    if not pairs:
        return "병목 TOP 3 변화\n- 시간 버킷 요약 로그가 아직 없어 비교할 수 없습니다."

    lines = ["병목 TOP 3 변화"]
    for (program_name, symbol), records in sorted(pairs.items())[:limit]:
        current = records[0]
        current_reasons = current.get("block_reason_counts", {}) or {}
        current_top = sorted(
            current_reasons.items(),
            key=lambda item: (-item[1], item[0]),
        )[:3]
        current_top_text = ", ".join(f"{name}:{count}" for name, count in current_top) or "없음"

        if len(records) < 2:
            lines.append(
                f"- {program_name} | {symbol} | 현재 {current_top_text} | 이전 비교 데이터 부족"
            )
            continue

        previous = records[1]
        previous_top = previous.get("top_block_reason") or "없음"
        previous_count = (previous.get("block_reason_counts", {}) or {}).get(previous_top, 0)
        lines.append(
            f"- {program_name} | {symbol} | 현재 {current_top_text} | 이전 대표 {previous_top}:{previous_count}"
        )
    return "\n".join(lines)


def build_filled_change_text(limit: int = 8) -> str:
    """최근 시간 버킷 기준 체결 변화 요약을 만든다."""
    pairs = load_latest_summary_pairs()
    if not pairs:
        return "체결 변화 요약\n- 시간 버킷 요약 로그가 아직 없어 비교할 수 없습니다."

    lines = ["체결 변화 요약"]
    for (program_name, symbol), records in sorted(pairs.items())[:limit]:
        current = records[0]
        current_filled = int(current.get("filled_count", 0))
        current_ready = int(current.get("entry_ready_count", 0)) + int(
            current.get("exit_ready_count", 0)
        )
        if len(records) < 2:
            lines.append(
                f"- {program_name} | {symbol} | 현재 ready {current_ready}, filled {current_filled} | 이전 비교 데이터 부족"
            )
            continue

        previous = records[1]
        previous_filled = int(previous.get("filled_count", 0))
        delta = current_filled - previous_filled
        delta_text = f"{delta:+d}"
        lines.append(
            f"- {program_name} | {symbol} | ready {current_ready}, filled {current_filled} | 이전 대비 {delta_text}"
        )
    return "\n".join(lines)


def build_symbol_conclusion_text(limit: int = 8) -> str:
    """심볼별 핵심 한 줄 결론을 만든다."""
    base_dir = Path("structured_logs/live")
    if not base_dir.exists():
        return "심볼별 핵심 한 줄 결론\n- 구조화 전략 로그가 아직 없습니다."

    rows = analyze_strategy_logs.build_summary_rows(base_dir)
    if not rows:
        return "심볼별 핵심 한 줄 결론\n- 아직 집계할 전략 로그가 없습니다."

    def build_conclusion(row: dict) -> str:
        top_reason = row.get("top_block_reason", "")
        side = row.get("side", "")
        if row.get("filled", 0) > 0:
            return "체결이 발생하고 있어 손익 품질을 함께 보면 됩니다."
        if top_reason == "no_bullish_signal":
            return "현재는 추세 전환 자체가 드물어 진입 기회가 적습니다."
        if top_reason == "distance_too_small":
            return "신호는 있으나 가격 이격도가 기준보다 작아 막히고 있습니다."
        if top_reason == "volume_low":
            return "거래량이 평균 대비 부족해 마지막 진입 관문을 통과하지 못하고 있습니다."
        if top_reason in {"volatility_low", "atr_low"}:
            return "시장 움직임이 작아 변동성 기준을 통과하지 못하고 있습니다."
        if top_reason == "higher_timeframe_not_bullish":
            return "단기 신호가 나와도 상위 추세와 맞지 않아 진입이 보류되고 있습니다."
        if top_reason == "no_exit_signal" and side == "exit":
            return "보유 포지션 청산 신호가 아직 나오지 않고 있습니다."
        if top_reason == "no_position" and side == "exit":
            return "현재 보유 포지션이 없어 청산 이벤트는 발생하지 않습니다."
        return "아직 표본이 적어 조금 더 로그를 쌓아보는 것이 좋습니다."

    lines = ["심볼별 핵심 한 줄 결론"]
    for row in sorted(rows, key=lambda item: (item["program_name"], item["symbol"], item["side"]))[:limit]:
        lines.append(
            f"- {row['program_name']} | {row['symbol']} {row['side']} | {build_conclusion(row)}"
        )
    return "\n".join(lines)


def build_daily_report_text(settings: ListenerSettings, label: str) -> str:
    """정해진 시간에 보낼 일일 리포트 문구를 만든다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "\n\n".join(
        [
            f"{label} 일일 리포트",
            f"기준 시각: {now}",
            build_pnl_text(),
            build_positions_text(settings),
            build_analysis_text(settings),
            build_bottleneck_change_text(),
            build_filled_change_text(),
            build_symbol_conclusion_text(),
            build_recent_trades_text(),
            build_today_skip_summary_text(),
        ]
    )


def is_today_timestamp(ts: str) -> bool:
    """로그 타임스탬프가 오늘 날짜인지 확인한다."""
    return ts.startswith(datetime.now().strftime("%Y-%m-%d"))


def iter_log_lines(filename: str) -> list[str]:
    """같은 이름의 날짜별 로그 파일 줄 목록을 모두 읽는다."""
    return read_all_lines(iter_files("logs", filename))


def latest_log_file(filename: str) -> Path | None:
    """같은 이름의 날짜별 로그 중 가장 최근 파일을 반환한다."""
    return latest_file("logs", filename)


def build_recent_trades_text(limit: int = 5) -> str:
    """오늘 발생한 최근 체결 내역을 요약한다."""
    records: list[dict] = []
    for path in iter_files("trade_logs", "trade_history.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                continue
            if not is_today_timestamp(str(record.get("recorded_at_local", ""))):
                continue
            records.append(record)

    if not records:
        return "최근 체결 내역\n- 오늘 발생한 체결 내역이 아직 없습니다."

    records.sort(key=lambda item: str(item.get("recorded_at_local", "")), reverse=True)
    lines = ["최근 체결 내역"]
    for record in records[:limit]:
        ts = str(record.get("recorded_at_local", "")).replace("T", " ")
        exchange_name = str(record.get("exchange_name", record.get("exchange", ""))).upper()
        symbol = str(record.get("symbol", ""))
        side = str(record.get("side", "")).lower()
        amount = safe_float(record.get("amount"))
        order_value_quote = safe_float(record.get("order_value_quote"))
        quote_currency = str(record.get("quote_currency", "")).strip().upper()
        pnl_pct = safe_float(record.get("net_realized_pnl_pct"))
        if pnl_pct is None:
            pnl_pct = safe_float(record.get("realized_pnl_pct"))
        reason = str(record.get("reason", "")).strip() or "-"

        decimals = 0 if quote_currency == "KRW" else 4
        amount_text = "-" if amount is None else format_number(amount, 8)
        value_text = (
            "-"
            if order_value_quote is None or not quote_currency
            else f"{format_number(order_value_quote, decimals)} {quote_currency}"
        )
        pnl_text = "-" if pnl_pct is None else f"{pnl_pct:.3f}%"
        side_label = "매수" if side == "buy" else "매도"

        lines.append(
            f"- {ts} | {exchange_name} | {symbol} | {side_label} | "
            f"수량 {amount_text} | 금액 {value_text} | 손익 {pnl_text} | 사유 {reason}"
        )
    return "\n".join(lines)


def summarize_skip_reasons(filename: str) -> dict[str, int]:
    """오늘 로그에서 스킵 사유 발생 횟수를 센다."""
    counts: dict[str, int] = {}

    for line in iter_log_lines(filename):
        stripped = line.strip()
        if not stripped.startswith(f"[{datetime.now().strftime('%Y-%m-%d')}"):
            continue
        for label, pattern in SKIP_REASON_PATTERNS:
            if pattern in stripped:
                counts[label] = counts.get(label, 0) + 1
                break

    return counts


def map_strategy_reason_to_label(
    reason: str,
    actual: dict[str, object] | None,
    required: dict[str, object] | None,
) -> str:
    """구조화 전략 로그의 reason 코드를 사용자용 스킵 사유 라벨로 바꾼다."""
    actual = actual or {}
    required = required or {}

    if reason in {"no_bullish_signal", "no_entry_signal"}:
        return "조건 미충족 대기"
    if reason == "distance_too_small":
        return "이격도 부족"
    if reason == "distance_too_large":
        return "이격도 과다"
    if reason == "volume_low":
        return "거래량 부족"
    if reason in {"volatility_low", "atr_low", "volatility_out_of_range", "atr_high"}:
        return "변동성 범위 이탈"
    if reason == "higher_timeframe_not_bullish":
        return "상위 타임프레임 불일치"
    if reason == "cooldown_active":
        return "쿨다운"
    if reason == "avg_price_rule_block":
        return "추가 매수 조건 미충족"
    if reason in {"order_value_too_small", "order_amount_too_small", "insufficient_balance"}:
        return "주문 금액 부족"
    if reason == "daily_loss_limit_reached":
        return "일일 손실 제한"
    if reason == "position_exists":
        return "기존 포지션 보유 중"
    if reason == "no_exit_signal":
        return "청산 신호 대기"
    if reason == "no_position":
        return "포지션 없음"

    # reason 코드가 낯설어도 actual/required 값을 보고 최대한 안정적으로 분류한다.
    if "volume_ratio" in actual and "min_volume_ratio" in required:
        return "거래량 부족"
    if "confirm_bullish" in actual and "confirm_bullish" in required:
        return "상위 타임프레임 불일치"
    if "atr_pct" in actual or "min_atr_pct" in required:
        return "변동성 범위 이탈"
    if "gap_pct" in actual or "min_gap_pct" in required:
        return "이격도 부족"
    return "기타"


def summarize_skip_reasons_from_structure(program_name: str) -> dict[str, int]:
    """오늘 구조화 전략 로그에서 스킵 사유를 센다."""
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    counts: dict[str, int] = {}
    for record in analyze_strategy_logs.read_program_records(
        Path("structured_logs/live"),
        program_name,
        "strategy.jsonl",
    ):
        if record.get("log_type") != "strategy":
            continue
        if record.get("result") != "blocked":
            continue
        recorded_local = str(record.get("recorded_at_local", ""))
        if not recorded_local.startswith(today_prefix):
            continue
        label = map_strategy_reason_to_label(
            str(record.get("reason", "")),
            record.get("actual") if isinstance(record.get("actual"), dict) else {},
            record.get("required") if isinstance(record.get("required"), dict) else {},
        )
        counts[label] = counts.get(label, 0) + 1
    return counts


def build_today_skip_summary_text(limit: int = 6) -> str:
    """오늘 스킵 사유를 거래소별로 요약한다."""
    sections = ["오늘 스킵 사유 요약"]

    for (exchange_name, filename), (_, program_name) in zip(
        PROGRAM_LOG_SOURCES,
        PROGRAM_STRUCTURE_SOURCES,
    ):
        counts = summarize_skip_reasons_from_structure(program_name)
        if not counts:
            counts = summarize_skip_reasons(filename)
        sections.append(f"[{exchange_name}]")
        if not counts:
            sections.append("- 오늘 집계된 스킵 사유가 아직 없습니다.")
            continue

        sorted_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        for label, count in sorted_counts[:limit]:
            sections.append(f"- {label}: {count}회")

    return "\n".join(sections)


def read_recent_lines(path: Path | None, line_count: int) -> list[str]:
    """파일 끝부분의 최근 줄만 읽는다."""
    if path is None or not path.exists():
        return ["로그 파일이 없습니다."]

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return ["로그 내용이 없습니다."]
    return lines[-line_count:]


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


def read_recent_lines_by_symbol(
    filename: str,
    line_count: int,
    symbol_order: list[str] | None = None,
    lookback_multiplier: int = 20,
) -> dict[str, list[str]]:
    """파일 끝부분에서 심볼별 최근 줄을 모아 반환한다."""
    path = latest_log_file(filename)
    if path is None or not path.exists():
        return {"공통": ["로그 파일이 없습니다."]}

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return {"공통": ["로그 내용이 없습니다."]}

    lookback_count = max(line_count * lookback_multiplier, 80)
    recent_lines = lines[-lookback_count:]
    grouped: dict[str, list[str]] = {}

    for line in recent_lines:
        symbol = extract_symbol_from_log_line(line) or "공통"
        grouped.setdefault(symbol, []).append(line)

    trimmed = {
        symbol: entries[-line_count:]
        for symbol, entries in grouped.items()
        if entries
    }

    has_symbol_specific_logs = any(symbol != "공통" for symbol in trimmed)
    if has_symbol_specific_logs and "공통" in trimmed:
        trimmed.pop("공통", None)

    if not symbol_order:
        return trimmed

    ordered: dict[str, list[str]] = {}
    for symbol in symbol_order:
        if symbol in trimmed:
            ordered[symbol] = trimmed[symbol]
    for symbol, entries in trimmed.items():
        if symbol not in ordered:
            ordered[symbol] = entries
    return ordered


def build_last_logs_text(settings: ListenerSettings) -> str:
    """최근 운영 로그 요약 문구를 만든다."""
    lines = ["최근 운영 로그"]
    symbol_orders = {
        "OKX 알트": load_alt_symbols("okx"),
        "업비트 알트": load_alt_symbols("upbit"),
        "OKX BTC": [symbol for symbol in settings.okx_symbols if symbol.startswith("BTC/")],
        "업비트 BTC": [symbol for symbol in settings.upbit_symbols if symbol.startswith("BTC/")],
    }

    for label, filename in PROGRAM_LOG_SOURCES:
        grouped_lines = read_recent_lines_by_symbol(
            filename,
            settings.recent_log_line_count,
            symbol_order=symbol_orders.get(label),
        )
        lines.append("")
        lines.append(f"[{label}]")
        for symbol, recent_lines in grouped_lines.items():
            lines.append(f"- {symbol}")
            lines.extend(
                f"  {format_recent_log_line_for_telegram(line)}"
                for line in recent_lines
            )
    return "\n".join(lines)


def build_response_text(command: str, settings: ListenerSettings) -> str:
    """명령에 맞는 응답 문자열을 만든다."""
    if command == "/status":
        return "\n\n".join(
            [
                bot_manager.build_status_text(use_color=False, exclude_current=False),
                build_runtime_guard_status_text(settings),
            ]
        )
    if command == "/test":
        return "텔레그램 테스트 메시지입니다. 현재 알림과 명령 응답이 정상 동작 중입니다."
    if command == "/positions":
        return build_positions_text(settings)
    if command == "/pnl":
        return build_pnl_text()
    if command == "/analysis":
        return build_analysis_text(settings)
    if command == "/regime":
        return build_regime_text(settings)
    if command == "/weekly":
        return build_weekly_report_text(settings)
    if command == "/last":
        return build_last_logs_text(settings)
    if command in {"/start", "/help"}:
        return build_help_text()
    return f"알 수 없는 명령입니다.\n\n{build_help_text()}"


def extract_message(update: dict) -> tuple[str | None, str | None]:
    """업데이트에서 chat id 와 텍스트를 꺼낸다."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None, None

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text")
    if chat_id is None or not text:
        return None, None
    return str(chat_id), text


def extract_callback_query(
    update: dict,
) -> tuple[str | None, str | None, str | None]:
    """업데이트에서 callback query 정보를 추출한다."""
    callback = update.get("callback_query")
    if not isinstance(callback, dict):
        return None, None, None
    callback_id = callback.get("id")
    data = callback.get("data")
    message = callback.get("message") or {}
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    if callback_id is None or data is None or chat_id is None:
        return None, None, None
    return str(chat_id), str(callback_id), str(data)


def answer_callback_query(bot_token: str, callback_id: str, text: str) -> None:
    """callback query 응답 팝업을 보낸다."""
    telegram_api_request(
        bot_token,
        "answerCallbackQuery",
        payload={"callback_query_id": callback_id, "text": text},
        timeout=10,
    )


def send_direct_text(
    bot_token: str,
    chat_id: str,
    text: str,
) -> tuple[bool, str | None]:
    """텔레그램 Bot API 로 즉시 텍스트를 전송한다."""
    result, error = telegram_api_request(
        bot_token,
        "sendMessage",
        payload={"chat_id": chat_id, "text": format_telegram_text_numbers(text)},
        timeout=15,
    )
    return (result is not None), error


def map_incident_exchange_to_program(exchange_name: str) -> str | None:
    """인시던트 거래소 라벨을 bot_manager 대상 이름으로 바꾼다."""
    normalized = exchange_name.strip().upper()
    mapping = {
        "OKX": "okx",
        "UPBIT": "upbit",
        "OKX-BTC": "okx_btc",
        "UPBIT-BTC": "upbit_btc",
        "TELEGRAM-LISTENER": "telegram",
        "COLLECTOR": "collector",
    }
    return mapping.get(normalized)


def restart_managed_program(target: str) -> tuple[bool, str]:
    """관리 대상 프로그램을 stop/start 순서로 재기동한다."""
    cmd_prefix = [sys.executable, "bot_manager.py"]
    workdir = Path(__file__).resolve().parent
    stop_result = subprocess.run(
        [*cmd_prefix, "stop", target],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    start_result = subprocess.run(
        [*cmd_prefix, "start", target],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    ok = stop_result.returncode == 0 and start_result.returncode == 0
    detail = (
        f"stop={stop_result.returncode}, start={start_result.returncode}\n"
        f"{start_result.stdout.strip() or start_result.stderr.strip() or '출력 없음'}"
    )
    return ok, detail


def handle_incident_callback(
    notifier,
    chat_id: str,
    callback_id: str,
    callback_data: str,
    logger: BotLogger,
) -> None:
    """인시던트 승인형 버튼 callback 을 처리한다."""
    log = logger.log
    parts = callback_data.split(":", 2)
    if len(parts) != 3 or parts[0] != "inc":
        answer_callback_query(notifier.bot_token, callback_id, "알 수 없는 버튼입니다.")
        return

    action, incident_id = parts[1], parts[2]
    incident = find_incident(incident_id)
    if incident is None:
        answer_callback_query(notifier.bot_token, callback_id, "인시던트를 찾지 못했습니다.")
        return

    if action == "detail":
        answer_callback_query(notifier.bot_token, callback_id, "상세 정보를 전송합니다.")
        _, error = send_direct_text(
            notifier.bot_token,
            chat_id,
            (
                f"[인시던트 상세]\n"
                f"ID: {incident['id']}\n"
                f"거래소: {incident['exchange_name']}\n"
                f"심볼: {incident['symbol']}\n"
                f"상태: {incident.get('status', '-')}\n"
                f"발생 횟수: {incident.get('count', 1)}\n"
                f"처음 발생: {incident.get('created_at', '-')}\n"
                f"마지막 발생: {incident.get('last_seen_at', '-')}\n"
                f"내용: {incident.get('detail', '-')}"
            ),
        )
        if error:
            log(f"인시던트 상세 전송 실패: {error}")
        return

    if action == "ignore":
        update_incident_status(incident_id, status="ignored", action="ignore")
        answer_callback_query(notifier.bot_token, callback_id, "무시 처리했습니다.")
        return

    if action == "fix":
        update_incident_status(incident_id, status="fix_requested", action="fix")
        answer_callback_query(notifier.bot_token, callback_id, "수정 요청으로 기록했습니다.")
        _, error = send_direct_text(
            notifier.bot_token,
            chat_id,
            (
                f"[수정 요청 접수]\n"
                f"ID: {incident['id']}\n"
                f"거래소: {incident['exchange_name']}\n"
                f"심볼: {incident['symbol']}\n"
                f"내용: {incident.get('detail', '-')}\n"
                f"현재 구현 범위에서는 요청만 기록하고, 실제 코드 패치는 수동/Codex 세션에서 진행합니다."
            ),
        )
        if error:
            log(f"수정 요청 메시지 전송 실패: {error}")
        return

    if action == "restart":
        target = map_incident_exchange_to_program(str(incident.get("exchange_name", "")))
        if not target:
            answer_callback_query(notifier.bot_token, callback_id, "재기동 대상 매핑에 실패했습니다.")
            return
        ok, detail = restart_managed_program(target)
        update_incident_status(
            incident_id,
            status="restart_requested" if ok else "restart_failed",
            action="restart",
        )
        answer_callback_query(
            notifier.bot_token,
            callback_id,
            "재기동 완료" if ok else "재기동 실패",
        )
        _, error = send_direct_text(
            notifier.bot_token,
            chat_id,
            (
                f"[재기동 {'완료' if ok else '실패'}]\n"
                f"ID: {incident['id']}\n"
                f"대상: {target}\n"
                f"{detail}"
            ),
        )
        if error:
            log(f"재기동 결과 메시지 전송 실패: {error}")
        return

    answer_callback_query(notifier.bot_token, callback_id, "지원하지 않는 버튼입니다.")


def load_report_state(path: Path) -> dict[str, str]:
    """일일 리포트 전송 상태를 읽는다."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}


def save_report_state(path: Path, state: dict[str, str]):
    """일일 리포트 전송 상태를 저장한다."""
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def maybe_send_scheduled_reports(
    notifier, settings: ListenerSettings, logger: BotLogger
):
    """정해진 리포트 전송 시각이면 슬롯별로 한 번만 전송한다."""
    if not settings.daily_report_enabled:
        return

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    report_state = load_report_state(settings.report_state_path)

    slots = [
        ("morning", settings.morning_report_hour, "아침 8시"),
        ("noon", settings.noon_report_hour, "오후 12시"),
        ("evening", settings.evening_report_hour, "저녁 6시"),
        ("night", settings.night_report_hour, "밤 9시"),
    ]

    for slot_name, report_hour, label in slots:
        state_key = f"{slot_name}_date"
        if now.hour != report_hour:
            continue
        if report_state.get(state_key) == today:
            continue

        text = build_daily_report_text(settings, label)
        sent, error = send_text_in_chunks(notifier, text)
        result_text = "성공" if sent else f"실패 ({error})"
        logger.log(f"{label} 일일 리포트 전송 결과: {result_text}")
        if sent:
            report_state[state_key] = today
            save_report_state(settings.report_state_path, report_state)

    if not settings.weekly_report_enabled:
        return

    if now.weekday() != settings.weekly_report_weekday:
        return
    if now.hour != settings.weekly_report_hour:
        return

    week_key = now.strftime("%G-W%V")
    if report_state.get("weekly_date") == week_key:
        return

    text = build_weekly_report_text(settings)
    sent, error = send_text_in_chunks(notifier, text)
    result_text = "성공" if sent else f"실패 ({error})"
    logger.log(f"주간 리포트 전송 결과: {result_text}")
    if sent:
        report_state["weekly_date"] = week_key
        save_report_state(settings.report_state_path, report_state)


def send_test_message() -> int:
    """즉시 테스트 메시지를 전송하고 종료한다."""
    notifier = load_telegram_notifier()
    if not notifier.enabled or not notifier.bot_token or not notifier.chat_id:
        print("텔레그램 설정이 비어 있어 테스트 메시지를 전송할 수 없습니다.")
        return 1

    text = (
        "텔레그램 테스트 메시지입니다.\n"
        "알림 설정과 봇 토큰, chat id 연결이 정상인지 확인할 때 사용합니다."
    )
    sent, error = notifier.send_message_detailed(text)
    if sent:
        print("텔레그램 테스트 메시지 전송 성공")
    else:
        print(f"텔레그램 테스트 메시지 전송 실패: {error}")
    return 0 if sent else 1


def build_parser() -> argparse.ArgumentParser:
    """명령행 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="텔레그램 명령 리스너")
    parser.add_argument(
        "--send-test",
        action="store_true",
        help="즉시 테스트 메시지를 전송하고 종료합니다.",
    )
    return parser


def run_listener():
    """텔레그램 명령 리스너 메인 루프."""
    notifier = load_telegram_notifier()
    settings = load_listener_settings()
    logger = BotLogger("telegram_command_listener")
    log = logger.log

    if not notifier.enabled or not notifier.bot_token or not notifier.chat_id:
        log("텔레그램 설정이 비어 있어 명령 리스너를 시작하지 않습니다.")
        return

    offset = initialize_offset_if_needed(notifier.bot_token, settings, logger)
    log("텔레그램 명령 리스너를 시작합니다.")
    last_poll_error: str | None = None
    last_runtime_error: str | None = None

    while True:
        try:
            updates, poll_error = get_updates(notifier.bot_token, offset=offset, timeout=20)
            if poll_error:
                if poll_error != last_poll_error:
                    log(f"텔레그램 업데이트 조회 실패: {poll_error}")
                    last_poll_error = poll_error
                updates = []
            else:
                last_poll_error = None

            for update in updates:
                offset = max(offset, int(update["update_id"]) + 1)
                save_offset(settings.offset_path, offset)

                callback_chat_id, callback_id, callback_data = extract_callback_query(update)
                if callback_chat_id is not None and callback_id is not None and callback_data is not None:
                    if callback_chat_id != notifier.chat_id:
                        log(f"허용되지 않은 chat_id({callback_chat_id}) callback 은 무시합니다.")
                        continue
                    log(f"callback 수신: {callback_data}")
                    handle_incident_callback(
                        notifier,
                        callback_chat_id,
                        callback_id,
                        callback_data,
                        logger,
                    )
                    continue

                chat_id, text = extract_message(update)
                if chat_id is None or text is None:
                    continue
                if chat_id != notifier.chat_id:
                    log(f"허용되지 않은 chat_id({chat_id}) 메시지는 무시합니다.")
                    continue

                command = normalize_command(text)
                log(f"명령 수신: {command}")
                response_text = build_response_text(command, settings)
                sent, error = send_text_in_chunks(notifier, response_text)
                result_text = "성공" if sent else f"실패 ({error})"
                log(f"응답 전송 결과: {result_text}")
        except Exception as e:
            log(f"텔레그램 명령 처리 중 에러 발생: {repr(e)}")
            error_signature = f"listener:{repr(e)}"
            if error_signature != last_runtime_error:
                notifier.notify_error_message("TELEGRAM-LISTENER", "listener", repr(e))
                last_runtime_error = error_signature

        try:
            maybe_send_scheduled_reports(notifier, settings, logger)
        except Exception as e:
            log(f"일일 리포트 전송 중 에러 발생: {repr(e)}")
            error_signature = f"report:{repr(e)}"
            if error_signature != last_runtime_error:
                notifier.notify_error_message("TELEGRAM-LISTENER", "report", repr(e))
                last_runtime_error = error_signature

        time.sleep(settings.poll_interval_sec)


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.send_test:
        raise SystemExit(send_test_message())
    run_listener()
