"""
수정 요약
- 2026-05-26: 텔레그램 리스너의 한글 출력 인코딩을 UTF-8 로 고정하고 /analysis 거래량 후보/튜닝 diff 조회 비용을 줄여 응답 지연을 낮췄다.
- 2026-05-24: /analysis 본문에서 무거운 원시 구조화 로그 스캔을 빼고 시간 버킷 요약 기반 섹션으로 대체했다.
- 2026-05-24: /analysis, /regime 이 전체 로그를 읽다 중단되지 않도록 최신 날짜/최신 레코드 기반으로 제한했다.
- 2026-05-14: 시간 판정과 최근 로그 파일 helper 를 reporting.telegram_log_helpers 로 분리했다.
- 2026-05-14: 순수 명령/숫자/최근 로그 포맷 helper 를 reporting.telegram_formatting 으로 분리했다.
- 2026-04-28: /analysis 와 /weekly 에 decision journal 기반 의사결정 리뷰와 reflection 요약을 추가했다.
- 2026-05-11: 정기 리포트의 스킵 사유와 백테스트 대비 실거래 섹션을 구체 사유/가독성 중심으로 정리했다.
- 2026-05-06: 복합 리포트에서 빈 보조 섹션을 숨기고 핵심 판정이 먼저 보이도록 텔레그램 문구를 정리했다.
- 2026-05-06: /change 와 /shadow 명령으로 변경 효과 자동 비교와 미체결 후보 가상 추적 요약을 확인하도록 추가했다.
- 2026-04-24: 튜닝 비교 리포트가 오래된 diff 파일에 머무르지 않도록 최신 batch_summary 2개 비교 fallback 과 Sharpe/PF 표시를 추가
- 시간대 리포트, 최근 체결, 레짐/시장 요약, 최근 로그의 심볼 라벨 앞에 초록 원 배지를 붙여 텔레그램 가독성을 높임
- /analysis 와 /weekly 에 최신 튜닝 세트 diff 요약을 붙여 보수형 대비 혼합형 개선 여부를 바로 보이도록 확장
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
- /change
- /shadow

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
from datetime import datetime, timedelta
from pathlib import Path
from math import sqrt


UTF8_ENV_DEFAULTS = {
    "PYTHONIOENCODING": "utf-8",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
}


def configure_utf8_stdio() -> None:
    """텔레그램 리스너와 자식 명령의 한글 출력을 UTF-8 로 고정한다."""
    for key, value in UTF8_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except ValueError:
            continue


def utf8_child_env() -> dict[str, str]:
    """자식 명령에 전달할 UTF-8 환경을 만든다."""
    env = os.environ.copy()
    for key, value in UTF8_ENV_DEFAULTS.items():
        env.setdefault(key, value)
    return env


configure_utf8_stdio()

import analyze_logs
import analyze_strategy_logs
import bot_manager
from core.runtime.program_registry import TRADE_PROGRAM_SPECS
from btc_trend_settings import load_btc_trend_settings
from incident_manager import find_incident, update_incident_status
from bot_logger import BotLogger
from log_path_utils import iter_files, latest_file
from reporting.listener_runtime import (
    ListenerSettings,
    get_updates,
    initialize_offset_if_needed,
    load_listener_settings,
    load_report_state,
    save_offset,
    save_report_state,
    telegram_api_request,
)
from reporting.position_snapshot import (
    build_okx_positions_text,
    build_upbit_positions_text,
    format_exchange_error_text,
)
from reporting.telegram_formatting import (
    LOW_SIGNAL_SECTION_MARKERS,
    format_number,
    format_number_trunc,
    format_numeric_token_for_telegram,
    format_recent_log_line_for_telegram,
    format_symbol_badge,
    is_low_signal_section,
    join_report_sections,
    normalize_command,
    safe_float,
    send_text_in_chunks,
    split_telegram_text,
)
from reporting.telegram_log_helpers import (
    is_in_recent_days,
    is_today_timestamp,
    iter_log_lines,
    latest_log_file,
    parse_local_timestamp,
    read_recent_lines,
    read_recent_lines_by_symbol,
)
from reporting.decision_journal import build_recent_reflection_summary
from reporting.change_effect_report import (
    build_change_effect_report,
    format_change_effect_text,
)
from reporting.shadow_candidate_tracker import (
    build_shadow_candidate_report,
    format_shadow_candidate_text,
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

PROGRAM_LOG_SOURCES = tuple(
    (spec.report_label or spec.title, spec.log_name)
    for spec in TRADE_PROGRAM_SPECS
    if spec.log_name
)

PROGRAM_STRUCTURE_SOURCES = tuple(
    (spec.report_label or spec.title, spec.structure_name)
    for spec in TRADE_PROGRAM_SPECS
    if spec.structure_name
)

PROGRAM_LABELS = {
    spec.structure_name: (spec.report_label or spec.title)
    for spec in TRADE_PROGRAM_SPECS
    if spec.structure_name
}

PROGRAM_STRATEGY_TYPES = {
    spec.structure_name: spec.strategy_type
    for spec in TRADE_PROGRAM_SPECS
    if spec.structure_name and spec.strategy_type
}

PROGRAM_EXCHANGES = {
    spec.structure_name: spec.exchange
    for spec in TRADE_PROGRAM_SPECS
    if spec.structure_name and spec.exchange
}

OKX_TICKERS_URL = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
UPBIT_TICKER_ALL_URL = "https://api.upbit.com/v1/ticker/all?quote_currencies=KRW"
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


def positive_env_int(name: str, default: int) -> int:
    """환경 변수의 양수 정수 값을 읽는다."""
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return max(value, 1)


def analysis_recent_date_dirs() -> int:
    """텔레그램 분석 요약에 사용할 최신 분석 로그 날짜 수."""
    return positive_env_int("TELEGRAM_ANALYSIS_RECENT_DATE_DIRS", 1)


def regime_latest_date_dirs() -> int:
    """레짐 계산에 사용할 최신 분석 로그 날짜 수."""
    return positive_env_int("TELEGRAM_REGIME_LOOKBACK_DATE_DIRS", 3)


def structured_recent_date_dirs() -> int:
    """텔레그램 퍼널 요약에 사용할 최신 구조화 로그 날짜 수."""
    return positive_env_int("TELEGRAM_STRUCTURED_RECENT_DATE_DIRS", 1)


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
        "- /change : 최신 변경 전후 효과 자동 비교\n"
        "- /shadow : 미체결 후보 가상 추적 요약\n"
        "- /last : 최근 운영 로그 확인\n"
        "- /help : 도움말"
    )


def build_positions_text(settings: ListenerSettings) -> str:
    """현재 거래소별 잔고와 포지션 요약을 만든다."""
    sections = ["현재 포지션 요약"]
    sections.append(build_okx_positions_text(settings.okx_symbols, format_number=format_number))
    sections.append(build_upbit_positions_text(settings.upbit_symbols, format_number=format_number))
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
        lines.append(f"- {row['label']} | {format_symbol_badge(symbol)} | " + " | ".join(detail_parts))
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
            "📊 백테스트 대비 실거래\n"
            "- 비교 파일 없음: `reports/backtests/**/comparison.json` 이 없습니다.\n"
            "- 조치: `backtest_replay.py` 실행 후 `compare_backtest_to_live.py` 로 최신 기간 비교 파일을 생성해야 합니다."
        )

    lines = ["📊 백테스트 대비 실거래"]
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
        since = str(filters.get("since") or "-")
        until = str(filters.get("until") or "-")
        backtest_sell_count = int(backtest.get("sell_count", 0) or 0)
        live_sell_count = int(live.get("sell_count", 0) or 0)
        backtest_trade_count = int(backtest.get("trade_count", 0) or 0)
        live_trade_count = int(live.get("trade_count", 0) or 0)
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
        lines.append("")
        lines.append(f"- {format_symbol_badge(symbol)} | {label}")
        lines.append(f"  • 기간: {since} ~ {until}")
        if backtest_trade_count == 0 and live_trade_count == 0:
            lines.append("  • 값 없음: 백테스트/실거래 체결 표본이 모두 0건입니다.")
            if since.startswith("2099") or until.startswith("2099"):
                lines.append("  • 원인: 현재 comparison.json 의 비교 기간이 미래 테스트 기간이라 실제 체결 값이 비어 있습니다.")
            else:
                lines.append("  • 원인: 해당 비교 기간에 매수/매도 체결이 없거나 비교 파일이 오래된 기간으로 생성됐습니다.")
            lines.append("  • 조치: 최신 운영 기간으로 백테스트와 실거래 비교를 다시 생성해야 합니다.")
            continue

        lines.append(
            f"  • 표본: 백테스트 체결 {backtest_trade_count}건·매도 {backtest_sell_count}건 / "
            f"실거래 체결 {live_trade_count}건·매도 {live_sell_count}건"
        )
        lines.append(
            f"  • 차이: 승률 {live_win_rate - backtest_win_rate:+.2f}%p / "
            f"평균 순손익률 {live_avg_pnl - backtest_avg_pnl:+.4f}%p"
        )
        lines.append(
            f"  • 성과: 백테스트 {backtest_total_quote:.4f} / 실거래 {live_total_quote:.4f}"
        )
        lines.append(
            f"  • 종료 사유: 백테스트 `{backtest_top_reason}` / 실거래 `{live_top_reason}`"
        )
        if comments:
            lines.append(f"  • 해석: {' / '.join(str(comment) for comment in comments[:3])}")
    missing_symbols = sorted(set(settings.okx_symbols + settings.upbit_symbols) - covered_symbols)
    if missing_symbols:
        lines.append("")
        lines.append(f"- ⚠️ 비교 파일 없는 심볼: {', '.join(missing_symbols[:6])}")
        lines.append("  • 원인: 해당 심볼의 최신 `comparison.json` 이 `reports/backtests` 아래에 없습니다.")
        sample_symbol = missing_symbols[0]
        sample_exchange = "upbit" if sample_symbol.endswith("/KRW") else "okx"
        sample_slug = sample_symbol.replace("/", "_").replace("-", "_").lower()
        lines.append(
            "  • 권장 실행: "
            f".venv/bin/python backtest_report_runner.py snapshot --label auto_compare_{sample_slug} "
            f"--symbols {sample_symbol} --exchanges {sample_exchange}"
        )
    return "\n".join(lines)


def build_latest_tuning_diff_text(limit: int = 6) -> str:
    """가장 최근 튜닝 세트 diff 요약을 만든다."""
    latest_diff_path = latest_file("reports/backtest_batches", "diff_summary.json")

    rows: list[dict[str, object]] = []
    source_label = ""

    if latest_diff_path is not None:
        try:
            payload = json.loads(latest_diff_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            payload = []
        if isinstance(payload, list):
            rows = [row for row in payload if isinstance(row, dict)]
            source_label = latest_diff_path.parent.name

    if not rows:
        batch_paths = sorted(iter_files("reports/backtest_batches", "batch_summary.json"))
        if len(batch_paths) >= 2:
            latest_two = select_recent_batch_pair_with_activity(batch_paths)
            if latest_two is None:
                latest_two = sorted(batch_paths, key=lambda path: path.stat().st_mtime)[-2:]
            try:
                before_payload = json.loads(latest_two[0].read_text(encoding="utf-8"))
                after_payload = json.loads(latest_two[1].read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                before_payload = {}
                after_payload = {}
            rows = build_tuning_diff_rows_from_batch_summaries(before_payload, after_payload)
            source_label = f"{latest_two[0].parent.name} -> {latest_two[1].parent.name}"

    if not rows:
        return "최근 튜닝 세트 비교\n- 최신 diff_summary.json 또는 비교 가능한 batch_summary.json 이 없습니다."

    lines = ["최근 튜닝 세트 비교"]
    lines.append(f"- 기준 파일: {source_label}")
    for row in rows[:limit]:
        lines.append(format_tuning_diff_row(row))
    return "\n".join(lines)


def build_tuning_diff_rows_from_batch_summaries(
    before_payload: dict[str, object],
    after_payload: dict[str, object],
) -> list[dict[str, object]]:
    """두 batch_summary payload 에서 공통 심볼 기준 비교 행을 만든다."""
    before_rows = before_payload.get("rows", []) if isinstance(before_payload, dict) else []
    after_rows = after_payload.get("rows", []) if isinstance(after_payload, dict) else []
    if not isinstance(before_rows, list) or not isinstance(after_rows, list):
        return []

    def _to_map(rows: list[object]) -> dict[str, dict[str, object]]:
        mapped: dict[str, dict[str, object]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            exchange_name = str(row.get("exchange_name", "")).strip()
            symbol = str(row.get("symbol", "")).strip()
            if not exchange_name or not symbol:
                continue
            mapped[f"{exchange_name}::{symbol}"] = row
        return mapped

    before_map = _to_map(before_rows)
    after_map = _to_map(after_rows)
    common_keys = sorted(set(before_map) & set(after_map))
    rows: list[dict[str, object]] = []
    for key in common_keys:
        before_row = before_map[key]
        after_row = after_map[key]
        before_summary = before_row.get("summary", {}) if isinstance(before_row.get("summary"), dict) else {}
        after_summary = after_row.get("summary", {}) if isinstance(after_row.get("summary"), dict) else {}
        before_metrics = enrich_summary_metrics_from_result_dir(
            before_summary,
            result_dir=str(before_row.get("result_dir", "") or ""),
            timeframe=str(before_payload.get("timeframe", "1m") or "1m"),
        )
        after_metrics = enrich_summary_metrics_from_result_dir(
            after_summary,
            result_dir=str(after_row.get("result_dir", "") or ""),
            timeframe=str(after_payload.get("timeframe", "1m") or "1m"),
        )
        rows.append(
            {
                "key": key,
                "before_return_pct": float(before_summary.get("net_return_pct", 0.0) or 0.0),
                "after_return_pct": float(after_summary.get("net_return_pct", 0.0) or 0.0),
                "return_diff_pct": float(after_summary.get("net_return_pct", 0.0) or 0.0)
                - float(before_summary.get("net_return_pct", 0.0) or 0.0),
                "before_trade_count": int(before_summary.get("trade_count", 0) or 0),
                "after_trade_count": int(after_summary.get("trade_count", 0) or 0),
                "before_max_drawdown_pct": float(before_summary.get("max_drawdown_pct", 0.0) or 0.0),
                "after_max_drawdown_pct": float(after_summary.get("max_drawdown_pct", 0.0) or 0.0),
                "before_sharpe_ratio": before_metrics.get("sharpe_ratio"),
                "after_sharpe_ratio": after_metrics.get("sharpe_ratio"),
                "before_profit_factor": before_metrics.get("profit_factor"),
                "after_profit_factor": after_metrics.get("profit_factor"),
            }
        )
    return rows


def select_recent_batch_pair_with_activity(batch_paths: list[Path]) -> tuple[Path, Path] | None:
    """최신 batch 중 공통 심볼 거래가 있는 비교쌍을 고른다."""
    if len(batch_paths) < 2:
        return None
    sorted_paths = sorted(batch_paths, key=lambda path: path.stat().st_mtime, reverse=True)
    payloads: dict[Path, dict[str, object]] = {}
    for path in sorted_paths:
        try:
            payloads[path] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            payloads[path] = {}
    for newer_index, newer in enumerate(sorted_paths[:-1]):
        for older in sorted_paths[newer_index + 1:]:
            rows = build_tuning_diff_rows_from_batch_summaries(
                payloads.get(older, {}),
                payloads.get(newer, {}),
            )
            if any(
                int(row.get("before_trade_count", 0) or 0) > 0
                or int(row.get("after_trade_count", 0) or 0) > 0
                for row in rows
            ):
                return older, newer
    return None


def enrich_summary_metrics_from_result_dir(
    summary: dict[str, object],
    *,
    result_dir: str,
    timeframe: str,
) -> dict[str, float | None]:
    """summary 에 없는 Sharpe/PF 를 result_dir 파일에서 보강 계산한다."""
    sharpe_ratio = summary.get("sharpe_ratio")
    profit_factor = summary.get("profit_factor")
    if sharpe_ratio is not None and profit_factor is not None:
        return {
            "sharpe_ratio": float(sharpe_ratio),
            "profit_factor": float(profit_factor),
        }
    result_path = Path(result_dir)
    if not result_dir or not result_path.exists():
        return {
            "sharpe_ratio": None if sharpe_ratio is None else float(sharpe_ratio),
            "profit_factor": None if profit_factor is None else float(profit_factor),
        }
    if sharpe_ratio is None:
        sharpe_ratio = compute_sharpe_ratio_from_equity_curve(result_path / "equity_curve.jsonl", timeframe=timeframe)
    if profit_factor is None:
        profit_factor = compute_profit_factor_from_trades(result_path / "trades.jsonl")
    return {
        "sharpe_ratio": None if sharpe_ratio is None else float(sharpe_ratio),
        "profit_factor": None if profit_factor is None else float(profit_factor),
    }


def compute_profit_factor_from_trades(path: Path) -> float | None:
    """trades.jsonl 에서 profit factor 를 계산한다."""
    if not path.exists():
        return None
    gross_profit = 0.0
    gross_loss = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if str(payload.get("side", "")).lower() != "sell":
            continue
        pnl = payload.get("net_realized_pnl_quote")
        try:
            pnl_value = float(pnl)
        except (TypeError, ValueError):
            continue
        if pnl_value > 0:
            gross_profit += pnl_value
        elif pnl_value < 0:
            gross_loss += abs(pnl_value)
    if gross_loss <= 0:
        if gross_profit <= 0:
            return None
        return float("inf")
    return gross_profit / gross_loss


def compute_sharpe_ratio_from_equity_curve(path: Path, *, timeframe: str) -> float | None:
    """equity_curve.jsonl 에서 단순 annualized Sharpe 를 계산한다."""
    if not path.exists():
        return None
    equities: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            equities.append(float(payload["equity_quote"]))
        except (ValueError, KeyError, TypeError):
            continue
    if len(equities) < 3:
        return None
    returns: list[float] = []
    prev = equities[0]
    for equity in equities[1:]:
        if prev > 0:
            returns.append((equity / prev) - 1.0)
        prev = equity
    if len(returns) < 2:
        return None
    mean_return = sum(returns) / len(returns)
    variance = sum((value - mean_return) ** 2 for value in returns) / (len(returns) - 1)
    if variance <= 0:
        return None
    timeframe_minutes = 1
    timeframe_raw = timeframe.strip().lower()
    if timeframe_raw.endswith("m"):
        timeframe_minutes = max(1, int(timeframe_raw[:-1]))
    elif timeframe_raw.endswith("h"):
        timeframe_minutes = max(1, int(timeframe_raw[:-1]) * 60)
    periods_per_year = (365.0 * 24.0 * 60.0) / timeframe_minutes
    return (mean_return / sqrt(variance)) * sqrt(periods_per_year)


def format_tuning_diff_row(row: dict[str, object]) -> str:
    """튜닝 비교 1행을 텔레그램용 문자열로 포맷한다."""
    line = (
        f"- {row.get('key', '-')} | "
        f"수익률 {float(row.get('before_return_pct', 0.0) or 0.0):.2f}% -> {float(row.get('after_return_pct', 0.0) or 0.0):.2f}% "
        f"({float(row.get('return_diff_pct', 0.0) or 0.0):+,.2f}%p) | "
        f"거래 수 {int(row.get('before_trade_count', 0) or 0)} -> {int(row.get('after_trade_count', 0) or 0)} | "
        f"MDD {float(row.get('before_max_drawdown_pct', 0.0) or 0.0):.2f}% -> {float(row.get('after_max_drawdown_pct', 0.0) or 0.0):.2f}%"
    )
    before_sharpe = row.get("before_sharpe_ratio")
    after_sharpe = row.get("after_sharpe_ratio")
    if before_sharpe is not None or after_sharpe is not None:
        line += (
            f" | Sharpe {float(before_sharpe or 0.0):.3f} -> {float(after_sharpe or 0.0):.3f}"
        )
    before_profit_factor = row.get("before_profit_factor")
    after_profit_factor = row.get("after_profit_factor")
    if before_profit_factor is not None or after_profit_factor is not None:
        line += (
            f" | PF {float(before_profit_factor or 0.0):.3f} -> {float(after_profit_factor or 0.0):.3f}"
        )
    return line


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
        build_latest_tuning_diff_text(),
        build_bottleneck_change_text(),
        build_filled_change_text(),
        build_recent_reflection_summary(days=7),
        build_trade_quality_text(settings),
        build_profit_protect_text(),
        build_time_of_day_text(),
        build_volume_candidate_text(settings),
    ]
    return join_report_sections(sections)


def build_change_effect_text(hours: float = 6.0) -> str:
    """최신 git 변경 시점 기준 전후 효과 비교 문구를 만든다."""
    try:
        report = build_change_effect_report(hours=hours)
    except ValueError:
        return "변경 효과 자동 비교\n- 최신 git 변경 시각을 찾지 못해 비교할 수 없습니다."
    except Exception as exc:
        return f"변경 효과 자동 비교\n- 집계 중 오류가 발생했습니다: {exc}"
    return format_change_effect_text(report)


def build_shadow_candidate_summary_text(lookback_hours: float = 6.0) -> str:
    """미체결 후보 가상 추적 요약 문구를 만든다."""
    try:
        report = build_shadow_candidate_report(lookback_hours=lookback_hours)
    except Exception as exc:
        return f"미체결 후보 가상 추적\n- 집계 중 오류가 발생했습니다: {exc}"
    return format_shadow_candidate_text(report)


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
    for program_name in analyze_strategy_logs.find_program_names(
        base_dir,
        max_date_dirs=days,
    ):
        for record in analyze_strategy_logs.iter_program_records(
            base_dir,
            program_name,
            "strategy.jsonl",
            max_date_dirs=days,
        ):
            if not is_in_recent_days(str(record.get("recorded_at_local", "")), days, now=now):
                continue
            if str(record.get("side", "")) != "entry":
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

    lines = [f"최근 {days}일 진입 퍼널 병목"]
    rows = sorted(
        grouped.items(),
        key=lambda item: (-int(item[1]["scans"]), item[0][0], item[0][1], item[0][2]),
    )
    for (program_name, symbol, side), bucket in rows[:limit]:
        block_reasons = bucket["block_reasons"] if isinstance(bucket["block_reasons"], dict) else {}
        top_block_reason = "-"
        if block_reasons:
            top_block_reason = sorted(block_reasons.items(), key=lambda item: (-item[1], item[0]))[0][0]
        scans = int(bucket["scans"])
        ready = int(bucket["ready"])
        filled = int(bucket["filled"])
        top_block_count = int(block_reasons.get(top_block_reason, 0)) if block_reasons else 0
        ready_rate = (ready / scans) * 100 if scans else 0.0
        lines.append(
            f"- {program_name} | {format_symbol_badge(symbol)} | "
            f"scan {scans} / ready {ready} ({ready_rate:.2f}%) / 체결 {filled} | "
            f"병목 {top_block_reason} {top_block_count}회"
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
    return join_report_sections(
        [
            "주간 리포트",
            f"집계 구간: {start} ~ {end}",
            build_period_pnl_text(7, title="최근 7일 누적 실현 손익"),
            build_positions_text(settings),
            build_current_market_strategy_text(settings),
            build_backtest_comparison_text(settings),
            build_latest_tuning_diff_text(),
            build_recent_reflection_summary(days=7),
            build_weekly_trade_quality_text(7),
            build_weekly_profit_protect_text(7),
            build_weekly_funnel_text(7),
            build_weekly_time_of_day_text(7),
            build_volume_candidate_text(settings),
        ],
        skip_low_signal=True,
    )


def build_market_analysis_text(settings: ListenerSettings) -> str:
    """시장 분석 수집 로그 요약 문구를 만든다."""
    summaries = analyze_logs.build_recent_summaries(
        settings.analysis_log_dir,
        max_date_dirs=analysis_recent_date_dirs(),
    )
    managed_symbols = set(settings.okx_symbols + settings.upbit_symbols)
    summaries = [item for item in summaries if item.symbol in managed_symbols]
    if not summaries:
        return "분석 로그가 아직 없습니다. analysis_log_collector.py 가 더 수집한 뒤 다시 확인해 주세요."

    lines = ["시장 로그 분석 요약"]
    for item in summaries:
        lines.append(
            f"- {item.exchange.upper()} {format_symbol_badge(item.symbol)} | "
            f"수집 {item.count}건 | "
            f"평균 이격도 {item.avg_gap_pct:.4f}% | "
            f"평균 절대 변화율 {item.avg_abs_change_pct:.4f}% | "
            f"매수 {item.bullish_count}회 / 매도 {item.bearish_count}회"
        )
    return "\n".join(lines)


def load_latest_market_records(settings: ListenerSettings) -> list[dict]:
    """심볼별 최신 분석 로그 1건씩을 반환한다."""
    managed_symbols = set(settings.okx_symbols + settings.upbit_symbols)
    rows = analyze_logs.load_latest_records(
        settings.analysis_log_dir,
        symbols=managed_symbols,
        max_date_dirs=regime_latest_date_dirs(),
    )
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
            f"- {exchange} {format_symbol_badge(symbol)} | {snapshot.regime} | "
            f"거래량 {volume_ratio}배 | 변화율 {abs_change} | "
            f"이격도 {gap_pct} | RSI {rsi_text} | 준비 {ready_text}"
        )
    return "\n".join(lines)


def fetch_public_json(url: str, timeout: int | None = None) -> object:
    """공개 HTTP JSON 응답을 읽는다."""
    if timeout is None:
        timeout = positive_env_int("TELEGRAM_VOLUME_CANDIDATE_HTTP_TIMEOUT_SEC", 5)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_volume_candidate_text(settings: ListenerSettings) -> str:
    """최근 거래대금 기준 신규 분석 후보 코인을 거래소별로 요약한다."""
    lines = ["24시간 거래대금 기준 신규 후보 코인"]

    okx_candidates, okx_error = fetch_okx_volume_candidates(settings.okx_symbols)
    if okx_error:
        lines.append(f"- OKX: 후보 조회 실패 ({okx_error})")
    elif not okx_candidates:
        lines.append("- OKX: 새로 추가할 만한 상위 후보가 아직 없습니다.")
    else:
        okx_text = ", ".join(
            f"{symbol} ({format_number(quote_volume, 0)} USDT)"
            for symbol, quote_volume in okx_candidates
        )
        lines.append(f"- OKX: {okx_text}")

    upbit_candidates, upbit_error = fetch_upbit_volume_candidates(settings.upbit_symbols)
    if upbit_error:
        lines.append(f"- UPBIT: 후보 조회 실패 ({upbit_error})")
    elif not upbit_candidates:
        lines.append("- UPBIT: 새로 추가할 만한 상위 후보가 아직 없습니다.")
    else:
        upbit_text = ", ".join(
            f"{symbol} ({format_number(quote_volume, 0)} KRW)"
            for symbol, quote_volume in upbit_candidates
        )
        lines.append(f"- UPBIT: {upbit_text}")

    return "\n".join(lines)


def fetch_okx_volume_candidates(
    managed_symbols: list[str],
    *,
    limit: int = VOLUME_CANDIDATE_COUNT,
) -> tuple[list[tuple[str, float]], str | None]:
    """OKX 에서 24시간 거래대금 기준 신규 후보를 추린다."""
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

        rows = [
            (inst_id.replace("-", "/"), vol_quote)
            for inst_id, vol_quote in candidates
        ]
        return filter_new_volume_candidates(rows, managed_symbols, limit), None
    except Exception as exc:
        return [], format_telegram_request_error(exc)


def fetch_upbit_volume_candidates(
    managed_symbols: list[str],
    *,
    limit: int = VOLUME_CANDIDATE_COUNT,
) -> tuple[list[tuple[str, float]], str | None]:
    """업비트에서 24시간 거래대금 기준 신규 후보를 추린다."""
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

        fast_rows = [
            (market.replace("KRW-", "") + "/KRW", trade_price)
            for market, trade_price in candidates
        ]
        return filter_new_volume_candidates(fast_rows, managed_symbols, limit), None
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

    rows = analyze_strategy_logs.build_summary_rows(
        base_dir,
        max_date_dirs=structured_recent_date_dirs(),
    )
    if not rows:
        return "전략 퍼널 분석 요약\n- 아직 집계할 전략 퍼널 로그가 없습니다."
    rows = [row for row in rows if str(row.get("side", "")) == "entry"]
    if not rows:
        return "전략 퍼널 분석 요약\n- 집계된 진입 퍼널 로그가 아직 없습니다."

    def sort_key(row: dict) -> tuple:
        scans = int(row.get("scans", 0) or 0)
        ready = int(row.get("ready", 0) or 0)
        return (-scans, -ready, row.get("program_name", ""), row.get("symbol", ""))

    lines = ["진입 퍼널 병목 요약"]
    for row in sorted(rows, key=sort_key)[:limit]:
        scans = int(row.get("scans", 0) or 0)
        ready = int(row.get("ready", 0) or 0)
        filled = int(row.get("filled", 0) or 0)
        ready_rate = (ready / scans) * 100 if scans > 0 else 0.0
        top_block_count = int(row.get("top_block_count", 0) or 0)
        top_block_ratio = (top_block_count / scans) * 100 if scans > 0 else 0.0
        lines.append(
            f"- {row['program_name']} | {format_symbol_badge(str(row['symbol']))} | "
            f"scan {scans} / ready {ready} ({ready_rate:.2f}%) / 체결 {filled} | "
            f"병목 {row['top_block_reason']} {top_block_count}회 ({top_block_ratio:.1f}%)"
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

    rows = analyze_strategy_logs.build_filter_gap_rows(
        base_dir,
        max_date_dirs=structured_recent_date_dirs(),
    )
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

    lines = ["최근 1시간 병목 변화"]
    for (program_name, symbol), records in sorted(pairs.items())[:limit]:
        current = records[0]
        if int(current.get("scan_count", 0) or 0) <= 0:
            continue
        current_reasons = current.get("block_reason_counts", {}) or {}
        current_top = sorted(
            current_reasons.items(),
            key=lambda item: (-item[1], item[0]),
        )[:3]
        current_top_text = ", ".join(f"{name}:{count}" for name, count in current_top) or "없음"

        if len(records) < 2:
            lines.append(
                f"- {program_name} | {format_symbol_badge(symbol)} | 현재 {current_top_text} | 이전 비교 부족"
            )
            continue

        previous = records[1]
        previous_top = previous.get("top_block_reason") or "없음"
        current_top_reason = current_top[0][0] if current_top else "없음"
        trend = "변화 없음" if current_top_reason == previous_top else f"{previous_top} -> {current_top_reason}"
        lines.append(
            f"- {program_name} | {format_symbol_badge(symbol)} | {trend} | 현재 {current_top_text}"
        )
    return "\n".join(lines) if len(lines) > 1 else "최근 1시간 병목 변화\n- 의미 있는 진입 스캔 변화가 아직 없습니다."


def build_filled_change_text(limit: int = 8) -> str:
    """최근 시간 버킷 기준 체결 변화 요약을 만든다."""
    pairs = load_latest_summary_pairs()
    if not pairs:
        return "체결 변화 요약\n- 시간 버킷 요약 로그가 아직 없어 비교할 수 없습니다."

    lines = ["최근 1시간 체결 변화"]
    for (program_name, symbol), records in sorted(pairs.items())[:limit]:
        current = records[0]
        current_filled = int(current.get("filled_count", 0))
        current_ready = int(current.get("entry_ready_count", 0)) + int(
            current.get("exit_ready_count", 0)
        )
        if len(records) < 2:
            lines.append(
                f"- {program_name} | {format_symbol_badge(symbol)} | ready {current_ready}, 체결 {current_filled} | 이전 비교 부족"
            )
            continue

        previous = records[1]
        previous_filled = int(previous.get("filled_count", 0))
        previous_ready = int(previous.get("entry_ready_count", 0)) + int(previous.get("exit_ready_count", 0))
        delta = current_filled - previous_filled
        ready_delta = current_ready - previous_ready
        if current_ready == 0 and current_filled == 0 and previous_ready == 0 and previous_filled == 0:
            continue
        lines.append(
            f"- {program_name} | {format_symbol_badge(symbol)} | "
            f"ready {previous_ready}->{current_ready} ({ready_delta:+d}) | "
            f"체결 {previous_filled}->{current_filled} ({delta:+d})"
        )
    return "\n".join(lines) if len(lines) > 1 else "최근 1시간 체결 변화\n- ready/체결 변화가 아직 없습니다."


def build_symbol_conclusion_text(limit: int = 8) -> str:
    """심볼별 핵심 한 줄 결론을 만든다."""
    base_dir = Path("structured_logs/live")
    if not base_dir.exists():
        return "심볼별 핵심 한 줄 결론\n- 구조화 전략 로그가 아직 없습니다."

    rows = analyze_strategy_logs.build_summary_rows(
        base_dir,
        max_date_dirs=structured_recent_date_dirs(),
    )
    if not rows:
        return "심볼별 핵심 한 줄 결론\n- 아직 집계할 전략 로그가 없습니다."
    rows = [row for row in rows if str(row.get("side", "")) == "entry"]
    if not rows:
        return "심볼별 핵심 한 줄 결론\n- 아직 집계할 진입 전략 로그가 없습니다."

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
    for row in sorted(rows, key=lambda item: (-int(item.get("scans", 0) or 0), item["program_name"], item["symbol"]))[:limit]:
        lines.append(
            f"- {row['program_name']} | {format_symbol_badge(str(row['symbol']))} | {build_conclusion(row)}"
        )
    return "\n".join(lines)


def build_daily_report_text(settings: ListenerSettings, label: str) -> str:
    """정해진 시간에 보낼 일일 리포트 문구를 만든다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return join_report_sections(
        [
            f"{label} 일일 리포트",
            f"⏱ 기준 시각: {now}",
            build_pnl_text(),
            build_positions_text(settings),
            build_analysis_text(settings),
            build_bottleneck_change_text(),
            build_filled_change_text(),
            build_symbol_conclusion_text(),
            build_recent_trades_text(),
            build_today_skip_summary_text(),
        ],
        skip_low_signal=True,
    )


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
            f"- {ts} | {exchange_name} | {format_symbol_badge(symbol)} | {side_label} | "
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
    *,
    stage: str = "",
    side: str = "",
) -> str:
    """구조화 전략 로그의 reason 코드를 사용자용 스킵 사유 라벨로 바꾼다."""
    actual = actual or {}
    required = required or {}

    if reason == "no_bullish_signal":
        return "상승 전환 신호 미형성"
    if reason == "no_entry_signal":
        return "진입 신호 미형성"
    if reason == "trend_signal_missing":
        if "ema_aligned" in actual or "ema_spread_pct" in actual:
            return "BTC EMA 추세 진입 신호 미충족"
        return "추세 진입 신호 미충족"
    if reason == "mean_reversion_lower_reclaim_missing":
        return "평균회귀 하단 복귀 미확인"
    if reason == "mean_reversion_range_context_blocked":
        return "평균회귀 range 위치 부적합"
    if reason == "mean_reversion_atr_context_blocked":
        return "평균회귀 ATR 환경 부적합"
    if reason == "mean_reversion_falling_knife_blocked":
        return "평균회귀 낙폭 추격 위험"
    if reason == "entry_signal_unclassified_block":
        return "진입 신호 최종 미확정"
    if reason == "distance_too_small":
        return "이격도 부족"
    if reason == "distance_too_large":
        return "이격도 과다"
    if reason == "volume_low":
        return "거래량 부족"
    if reason == "volume_spike_too_high":
        return "거래량 급등 추격 위험"
    if reason in {"volatility_low", "atr_low", "volatility_out_of_range", "atr_high"}:
        return "변동성 범위 이탈"
    if reason == "bb_width_out_of_range":
        return "볼린저 밴드폭 범위 이탈"
    if reason == "higher_timeframe_not_bullish":
        return "상위 타임프레임 불일치"
    if reason == "macd_filter_blocked":
        return "MACD 필터 미통과"
    if reason == "rsi_filter_blocked":
        return "RSI 필터 미통과"
    if reason == "symbol_regime_blocks_entry":
        return "현재 레짐 신규진입 차단"
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
        if stage == "add_on_position":
            return "추가매수 대상 포지션 없음"
        if side == "exit":
            return "청산 대상 포지션 없음"
        return "포지션 없음"

    # reason 코드가 낯설어도 actual/required 값을 보고 최대한 안정적으로 분류한다.
    if "symbol_regime" in actual and "symbol_regime_allows_entry" in required:
        return "현재 레짐 신규진입 차단"
    if "volume_ratio" in actual and "min_volume_ratio" in required:
        return "거래량 부족"
    if "volume_ratio" in actual and "max_volume_ratio" in required:
        return "거래량 급등 추격 위험"
    if "confirm_bullish" in actual and "confirm_bullish" in required:
        return "상위 타임프레임 불일치"
    if "rsi_filter_passed" in actual:
        return "RSI 필터 미통과"
    if "macd_filter_passed" in actual:
        return "MACD 필터 미통과"
    if "bb_width_pct" in actual:
        return "볼린저 밴드폭 범위 이탈"
    if "atr_pct" in actual or "min_atr_pct" in required:
        return "변동성 범위 이탈"
    if "gap_pct" in actual or "min_gap_pct" in required:
        return "이격도 부족"
    if reason:
        return f"세부 조건 미충족({reason})"
    if stage:
        return f"{stage} 단계 조건 미충족"
    return "세부 조건 미충족"


def summarize_skip_reasons_from_structure(program_name: str) -> dict[str, int]:
    """오늘 구조화 전략 로그에서 스킵 사유를 센다."""
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    counts: dict[str, int] = {}
    for record in analyze_strategy_logs.iter_program_records(
        Path("structured_logs/live"),
        program_name,
        "strategy.jsonl",
        max_date_dirs=1,
    ):
        if record.get("log_type") != "strategy":
            continue
        if record.get("result") != "blocked":
            continue
        recorded_local = str(record.get("recorded_at_local", ""))
        if not recorded_local.startswith(today_prefix):
            continue
        reason = str(record.get("reason", ""))
        stage = str(record.get("stage", ""))
        side = str(record.get("side", ""))
        if side and side != "entry":
            continue
        if stage == "add_on_position" and reason == "no_position":
            continue
        label = map_strategy_reason_to_label(
            reason,
            record.get("actual") if isinstance(record.get("actual"), dict) else {},
            record.get("required") if isinstance(record.get("required"), dict) else {},
            stage=stage,
            side=side,
        )
        counts[label] = counts.get(label, 0) + 1
    return counts


def build_today_skip_summary_text(limit: int = 6) -> str:
    """오늘 스킵 사유를 거래소별로 요약한다."""
    sections = ["🚦 오늘 진입 스킵 사유 요약", "- 집계 기준: 구조화 전략 로그의 `entry` 차단 사유만 반영합니다."]

    for (exchange_name, filename), (_, program_name) in zip(
        PROGRAM_LOG_SOURCES,
        PROGRAM_STRUCTURE_SOURCES,
    ):
        counts = summarize_skip_reasons_from_structure(program_name)
        if not counts:
            counts = summarize_skip_reasons(filename)
        sections.append("")
        sections.append(f"[{exchange_name}]")
        if not counts:
            sections.append("- 오늘 집계된 스킵 사유가 아직 없습니다.")
            continue

        sorted_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        for label, count in sorted_counts[:limit]:
            sections.append(f"• {label}: {count}회")

    return "\n".join(sections)


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
            lines.append(f"- {format_symbol_badge(symbol)}")
            lines.extend(
                f"  {format_recent_log_line_for_telegram(line)}"
                for line in recent_lines
            )
    return "\n".join(lines)


def build_response_text(command: str, settings: ListenerSettings) -> str:
    """명령에 맞는 응답 문자열을 만든다."""
    try:
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
        if command == "/change":
            return build_change_effect_text()
        if command == "/shadow":
            return build_shadow_candidate_summary_text()
        if command == "/last":
            return build_last_logs_text(settings)
        if command in {"/start", "/help"}:
            return build_help_text()
        return f"알 수 없는 명령입니다.\n\n{build_help_text()}"
    except Exception as exc:
        return (
            f"{command} 응답 생성 중 오류가 발생했습니다.\n"
            f"- 원인: {repr(exc)}\n"
            "- 리스너는 계속 실행 중이므로 잠시 뒤 다시 시도해 주세요."
        )


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
    workdir = Path(__file__).resolve().parents[1]
    stop_result = subprocess.run(
        [*cmd_prefix, "stop", target],
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=utf8_child_env(),
    )
    start_result = subprocess.run(
        [*cmd_prefix, "start", target],
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=utf8_child_env(),
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
                log(f"응답 생성 시작: {command}")
                response_text = build_response_text(command, settings)
                log(f"응답 생성 완료: {command} ({len(response_text)}자)")
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
