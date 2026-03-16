"""
수정 요약
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

- 텔레그램에서 /status, /positions, /pnl, /analysis, /last 명령을 받아 응답한다.
- 상태 조회는 bot_manager 의 관리 대상 상태 문자열을 재사용한다.
- 포지션 조회는 각 거래소 API 를 호출해 현재 잔고와 대략적인 평가 금액을 보여준다.
- 분석 조회는 analyze_logs 의 요약 함수를 재사용한다.
- 최근 로그 조회는 프로그램별 로그 파일 끝부분을 짧게 묶어서 보여준다.
- /test 명령과 즉시 테스트 전송 옵션으로 텔레그램 연결 상태를 점검할 수 있다.
- 아침 8시, 오후 12시, 저녁 6시, 밤 9시에 일일 리포트를 자동 전송할 수 있다.
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
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import ccxt
from dotenv import load_dotenv

import analyze_logs
import analyze_strategy_logs
import bot_manager
from bot_logger import BotLogger
from ma_crossover_bot import (
    create_okx_client,
    fetch_ohlcv as fetch_okx_ohlcv,
    get_spot_balances as get_okx_spot_balances,
    load_config as load_okx_config,
)
from telegram_notifier import load_telegram_notifier
from telegram_notifier import format_telegram_request_error
from trade_history_logger import estimate_round_trip_net_pnl
from strategy_settings import load_alt_symbols, load_managed_symbols
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
    ("OKX 알트", Path("logs/ma_crossover_bot.log")),
    ("업비트 알트", Path("logs/upbit_ma_crossover_bot.log")),
    ("OKX BTC", Path("logs/okx_btc_ema_trend_bot.log")),
    ("업비트 BTC", Path("logs/upbit_btc_ema_trend_bot.log")),
]

PROGRAM_STRUCTURE_SOURCES = [
    ("OKX 알트", "ma_crossover_bot"),
    ("업비트 알트", "upbit_ma_crossover_bot"),
    ("OKX BTC", "okx_btc_ema_trend_bot"),
    ("업비트 BTC", "upbit_btc_ema_trend_bot"),
]

OKX_TICKERS_URL = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
OKX_CANDLES_URL = "https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar=1D&limit=7"
UPBIT_TICKER_ALL_URL = "https://api.upbit.com/v1/ticker/all?quote_currencies=KRW"
UPBIT_CANDLES_URL = "https://api.upbit.com/v1/candles/days?market={market}&count=7"
VOLUME_CANDIDATE_COUNT = 3
STABLE_BASES = {"USDT", "USDC", "USDC.e", "USDD", "DAI"}


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


def format_number(value: float, decimals: int = 4) -> str:
    """지정 소수점 자리수와 천 단위 쉼표를 적용한 숫자 문자열을 만든다."""
    return f"{value:,.{decimals}f}"


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
        "- /last : 최근 운영 로그 확인\n"
        "- /help : 도움말"
    )


def build_positions_text(settings: ListenerSettings) -> str:
    """현재 거래소별 잔고와 포지션 요약을 만든다."""
    sections = ["현재 포지션 요약"]
    sections.append(build_okx_positions_text(settings.okx_symbols))
    sections.append(build_upbit_positions_text(settings.upbit_symbols))
    return "\n\n".join(sections)


def load_latest_entry_prices() -> dict[tuple[str, str], float]:
    """체결 이력에서 거래소/심볼별 최신 추정 진입가를 읽는다."""
    path = Path("trade_logs/trade_history.jsonl")
    if not path.exists():
        return {}

    latest_prices: dict[tuple[str, str], float] = {}
    latest_ts: dict[tuple[str, str], str] = {}

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
    path = Path("trade_logs/trade_history.jsonl")
    if not path.exists():
        return "오늘 누적 실현 손익\n- 체결 이력이 아직 없습니다."

    today_prefix = datetime.now().strftime("%Y-%m-%d")
    totals: dict[str, float] = {}
    trade_counts: dict[str, int] = {}
    estimated_counts: dict[str, int] = {}
    gross_fallback_counts: dict[str, int] = {}

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

        try:
            if net_value not in (None, ""):
                pnl_value = float(net_value)
            elif gross_value not in (None, ""):
                fee_rate_pct = record.get("fee_rate_pct")
                if fee_rate_pct in (None, ""):
                    exchange_name = str(record.get("exchange", "")).strip().upper()
                    if exchange_name == "UPBIT":
                        fee_rate_pct = os.getenv("UPBIT_FEE_RATE_PCT", "0.05")
                    elif exchange_name == "OKX":
                        fee_rate_pct = os.getenv("OKX_FEE_RATE_PCT", "1.0")

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
        lines.append(
            f"- {quote}: {format_number(totals[quote], decimals)} "
            f"({trade_counts.get(quote, 0)}건)"
        )
        estimated_count = estimated_counts.get(quote, 0)
        if estimated_count:
            lines.append(
                f"  참고: {estimated_count}건은 왕복 수수료를 적용해 순손익으로 재계산했습니다."
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
        build_strategy_funnel_text(),
        build_trade_quality_text(),
        build_filter_gap_text(),
        build_time_of_day_text(),
        build_volume_candidate_text(settings),
    ]
    return "\n\n".join(section for section in sections if section)


def build_market_analysis_text(settings: ListenerSettings) -> str:
    """시장 분석 수집 로그 요약 문구를 만든다."""
    records = analyze_logs.load_records(settings.analysis_log_dir)
    summaries = analyze_logs.build_summaries(records)
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


def build_trade_quality_text(limit: int = 8) -> str:
    """체결 품질 요약 문구를 만든다."""
    rows = analyze_strategy_logs.build_trade_quality_rows()
    if not rows:
        return "거래 품질 요약\n- 아직 집계할 체결 품질 로그가 없습니다."

    lines = ["거래 품질 요약"]
    for row in rows[:limit]:
        lines.append(
            f"- {row['program_name']} | {row['symbol']} | "
            f"거래 {row['trades']}건 | "
            f"평균 손익 {row['avg_net_pnl_pct']}% | "
            f"MFE {row['avg_mfe_pct']}% / MAE {row['avg_mae_pct']}% | "
            f"보유 {row['avg_holding_seconds']}초 | "
            f"트레일링 활성 {row['trailing_arm_rate']}"
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

    for program_dir in sorted(path for path in base_dir.iterdir() if path.is_dir()):
        summary_dir = program_dir / "summary_1h"
        if not summary_dir.exists():
            continue
        grouped: dict[tuple[str, str], list[dict]] = {}
        for path in summary_dir.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            key = (program_dir.name, str(record.get("symbol", "")))
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


def iter_log_lines(path: Path) -> list[str]:
    """로그 파일 줄 목록을 안전하게 읽는다."""
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def build_recent_trades_text(limit: int = 5) -> str:
    """오늘 발생한 최근 체결 내역을 요약한다."""
    events: list[tuple[str, str, str, str]] = []

    for exchange_name, path in PROGRAM_LOG_SOURCES:
        for line in iter_log_lines(path):
            match = TRADE_EVENT_RE.match(line.strip())
            if not match:
                continue
            ts = match.group("ts")
            if not is_today_timestamp(ts):
                continue
            events.append(
                (
                    ts,
                    exchange_name,
                    match.group("symbol"),
                    match.group("title"),
                )
            )

    if not events:
        return "최근 체결 내역\n- 오늘 발생한 체결 내역이 아직 없습니다."

    events.sort(key=lambda item: item[0], reverse=True)
    lines = ["최근 체결 내역"]
    for ts, exchange_name, symbol, title in events[:limit]:
        lines.append(f"- {ts} | {exchange_name} | {symbol} | {title}")
    return "\n".join(lines)


def summarize_skip_reasons(path: Path) -> dict[str, int]:
    """오늘 로그에서 스킵 사유 발생 횟수를 센다."""
    counts: dict[str, int] = {}

    for line in iter_log_lines(path):
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
    path = Path("structured_logs/live") / program_name / "strategy.jsonl"
    if not path.exists():
        return {}

    today_prefix = datetime.now().strftime("%Y-%m-%d")
    counts: dict[str, int] = {}
    for record in analyze_strategy_logs.read_jsonl(path):
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

    for (exchange_name, path), (_, program_name) in zip(
        PROGRAM_LOG_SOURCES,
        PROGRAM_STRUCTURE_SOURCES,
    ):
        counts = summarize_skip_reasons_from_structure(program_name)
        if not counts:
            counts = summarize_skip_reasons(path)
        sections.append(f"[{exchange_name}]")
        if not counts:
            sections.append("- 오늘 집계된 스킵 사유가 아직 없습니다.")
            continue

        sorted_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        for label, count in sorted_counts[:limit]:
            sections.append(f"- {label}: {count}회")

    return "\n".join(sections)


def read_recent_lines(path: Path, line_count: int) -> list[str]:
    """파일 끝부분의 최근 줄만 읽는다."""
    if not path.exists():
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
    path: Path,
    line_count: int,
    symbol_order: list[str] | None = None,
    lookback_multiplier: int = 20,
) -> dict[str, list[str]]:
    """파일 끝부분에서 심볼별 최근 줄을 모아 반환한다."""
    if not path.exists():
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

    for label, path in PROGRAM_LOG_SOURCES:
        grouped_lines = read_recent_lines_by_symbol(
            path,
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
        return bot_manager.build_status_text(use_color=False, exclude_current=False)
    if command == "/test":
        return "텔레그램 테스트 메시지입니다. 현재 알림과 명령 응답이 정상 동작 중입니다."
    if command == "/positions":
        return build_positions_text(settings)
    if command == "/pnl":
        return build_pnl_text()
    if command == "/analysis":
        return build_analysis_text(settings)
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
        sent, error = notifier.send_message_detailed(text[:3900])
        result_text = "성공" if sent else f"실패 ({error})"
        logger.log(f"{label} 일일 리포트 전송 결과: {result_text}")
        if sent:
            report_state[state_key] = today
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

                chat_id, text = extract_message(update)
                if chat_id is None or text is None:
                    continue
                if chat_id != notifier.chat_id:
                    log(f"허용되지 않은 chat_id({chat_id}) 메시지는 무시합니다.")
                    continue

                command = normalize_command(text)
                log(f"명령 수신: {command}")
                response_text = build_response_text(command, settings)
                sent, error = notifier.send_message_detailed(response_text[:3900])
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
