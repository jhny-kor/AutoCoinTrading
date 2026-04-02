"""
수정 요약
- 업비트 공개 웹소켓 시장데이터 수집기를 관리 대상 프로그램으로 추가하고 전체 시작 순서에 포함했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgramSpec:
    name: str
    script: str
    title: str
    report_label: str | None = None
    exchange: str | None = None
    strategy_type: str | None = None
    structure_name: str | None = None
    log_name: str | None = None


PROGRAM_SPECS: tuple[ProgramSpec, ...] = (
    ProgramSpec(
        name="okx",
        script="run/ma_crossover_bot.py",
        title="OKX 봇",
        report_label="OKX 알트",
        exchange="OKX",
        strategy_type="alt",
        structure_name="ma_crossover_bot",
        log_name="ma_crossover_bot.log",
    ),
    ProgramSpec(
        name="upbit",
        script="run/upbit_ma_crossover_bot.py",
        title="업비트 봇",
        report_label="업비트 알트",
        exchange="UPBIT",
        strategy_type="alt",
        structure_name="upbit_ma_crossover_bot",
        log_name="upbit_ma_crossover_bot.log",
    ),
    ProgramSpec(
        name="okx_btc",
        script="run/okx_btc_ema_trend_bot.py",
        title="OKX BTC EMA 봇",
        report_label="OKX BTC",
        exchange="OKX",
        strategy_type="btc",
        structure_name="okx_btc_ema_trend_bot",
        log_name="okx_btc_ema_trend_bot.log",
    ),
    ProgramSpec(
        name="upbit_btc",
        script="run/upbit_btc_ema_trend_bot.py",
        title="업비트 BTC EMA 봇",
        report_label="업비트 BTC",
        exchange="UPBIT",
        strategy_type="btc",
        structure_name="upbit_btc_ema_trend_bot",
        log_name="upbit_btc_ema_trend_bot.log",
    ),
    ProgramSpec(
        name="collector",
        script="run/analysis_log_collector.py",
        title="분석 수집기",
        report_label="분석 수집기",
        log_name="analysis_log_collector.log",
    ),
    ProgramSpec(
        name="upbit_stream",
        script="run/upbit_market_data_stream.py",
        title="업비트 웹소켓 수집기",
        report_label="업비트 웹소켓 수집기",
        log_name="upbit_market_data_stream.log",
    ),
    ProgramSpec(
        name="telegram",
        script="run/telegram_command_listener.py",
        title="텔레그램 명령 리스너",
        report_label="텔레그램 명령 리스너",
        log_name="telegram_command_listener.log",
    ),
)

PROGRAMS: dict[str, str] = {spec.name: spec.script for spec in PROGRAM_SPECS}
PROGRAM_TITLES: dict[str, str] = {spec.name: spec.title for spec in PROGRAM_SPECS}
PROGRAM_BY_NAME: dict[str, ProgramSpec] = {spec.name: spec for spec in PROGRAM_SPECS}
PROGRAM_CHOICES: tuple[str, ...] = tuple(spec.name for spec in PROGRAM_SPECS)
START_ALL_ORDER: tuple[str, ...] = (
    "collector",
    "upbit_stream",
    "telegram",
    "okx",
    "upbit",
    "okx_btc",
    "upbit_btc",
)
TRADE_PROGRAM_SPECS: tuple[ProgramSpec, ...] = tuple(
    spec for spec in PROGRAM_SPECS if spec.strategy_type is not None
)
