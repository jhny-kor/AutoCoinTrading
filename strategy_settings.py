"""
수정 요약
- 알트 전략에서 심볼별 부분익절/부분손절 대상과 비율을 .env 에서 읽도록 확장
- 공통 전략 버전 이름을 .env 에서 읽어 로그와 체결 이력에 함께 남길 수 있도록 확장
- 알트 봇에 보수형 trend_follow_entry 설정을 추가해 골든크로스가 아니어도 제한적으로 추세 유지 진입을 허용할 수 있게 개선
- 연속 MA 상단 유지와 직전 대비 상승 조건을 .env 에서 제어할 수 있도록 확장
- 심볼별 거래량 기준 오버라이드를 .env 에서 읽어 DOGE 같은 고변동 알트의 진입 품질을 코인별로 분리 조정할 수 있게 개선
- 알트 심볼 목록과 운영/분석 대상 심볼 목록도 공통으로 .env 에서 읽도록 확장
- 빈 문자열로 설정한 알트 심볼 목록은 기본값으로 되돌리지 않고 비활성화로 처리하도록 보정

공통 전략 설정 로더

- 두 거래소 봇이 같은 전략 값을 .env 에서 읽도록 돕는 모듈
- 공통 전략 값은 STRATEGY_ 접두사로 관리
- 최소 주문 금액은 거래소별로 달라서 별도 키를 사용
- 심볼별 이격도 기준 오버라이드를 .env 에서 읽을 수 있도록 지원
- 심볼별 익절률/손절률 오버라이드를 .env 에서 읽을 수 있도록 지원
- 상위 타임프레임 추세 필터 설정을 .env 에서 읽을 수 있도록 지원
- 거래량 필터와 변동성 필터 설정을 .env 에서 읽을 수 있도록 지원
- 심볼별 최소 주문 수량 오버라이드를 .env 에서 읽을 수 있도록 지원
- 알트 봇 감시 심볼과 텔레그램/분석 수집 대상 심볼도 공통 규칙으로 재사용할 수 있도록 지원
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_OKX_ALT_SYMBOLS = ["PI/USDT"]
DEFAULT_UPBIT_ALT_SYMBOLS = ["XRP/KRW"]
DEFAULT_OKX_BTC_SYMBOL = "BTC/USDT"
DEFAULT_UPBIT_BTC_SYMBOL = "BTC/KRW"


@dataclass(frozen=True)
class StrategySettings:
    """두 봇이 공통으로 사용하는 전략 설정 묶음."""

    version: str
    buy_split_ratio: float
    sell_split_ratio: float
    max_entry_count: int
    min_trade_interval_sec: int
    enable_trend_follow_entry: bool
    trend_follow_requires_prev_above_ma: bool
    trend_follow_requires_price_rising: bool
    enable_higher_timeframe_filter: bool
    higher_timeframe: str
    higher_timeframe_ma_period: int
    enable_volume_filter: bool
    volume_lookback: int
    min_volume_ratio: float
    min_volume_ratio_map: dict[str, float]
    enable_volatility_filter: bool
    volatility_lookback: int
    min_volatility_pct: float
    max_volatility_pct: float
    min_crossover_gap_pct: float
    averaging_down_gap_pct: float
    min_take_profit_pct: float
    stop_loss_pct: float
    min_buy_order_value: float
    loop_interval_sec: int
    min_crossover_gap_pct_map: dict[str, float]
    min_take_profit_pct_map: dict[str, float]
    stop_loss_pct_map: dict[str, float]
    min_order_amount_map: dict[str, float]
    partial_take_profit_symbols: tuple[str, ...]
    partial_stop_loss_symbols: tuple[str, ...]
    partial_take_profit_ratio: float
    partial_stop_loss_ratio: float

    def get_crossover_gap_pct(self, symbol: str) -> float:
        """심볼별 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.min_crossover_gap_pct_map.get(symbol, self.min_crossover_gap_pct)

    def get_take_profit_pct(self, symbol: str) -> float:
        """심볼별 익절률 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.min_take_profit_pct_map.get(symbol, self.min_take_profit_pct)

    def get_stop_loss_pct(self, symbol: str) -> float:
        """심볼별 손절률 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.stop_loss_pct_map.get(symbol, self.stop_loss_pct)

    def get_min_volume_ratio(self, symbol: str) -> float:
        """심볼별 거래량 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.min_volume_ratio_map.get(symbol, self.min_volume_ratio)

    def get_min_order_amount(self, symbol: str) -> float:
        """심볼별 최소 주문 수량 오버라이드가 있으면 그 값을, 없으면 0을 반환한다."""
        return self.min_order_amount_map.get(symbol, 0.0)

    def uses_partial_take_profit(self, symbol: str) -> bool:
        """심볼이 부분익절 대상인지 반환한다."""
        return symbol in self.partial_take_profit_symbols

    def uses_partial_stop_loss(self, symbol: str) -> bool:
        """심볼이 부분손절 대상인지 반환한다."""
        return symbol in self.partial_stop_loss_symbols


def parse_symbol_list(raw: str | None, default: list[str] | None = None) -> list[str]:
    """쉼표 구분 심볼 문자열을 중복 없이 정리한다."""
    if raw is None:
        source = default or []
    else:
        source = raw.split(",")

    result: list[str] = []
    seen: set[str] = set()
    for item in source:
        symbol = str(item).strip()
        if not symbol or symbol in seen:
            continue
        result.append(symbol)
        seen.add(symbol)
    return result


def parse_symbol_float_map(raw: str) -> dict[str, float]:
    """BTC/USDT:0.15,PI/USDT:2.5 형태의 문자열을 사전으로 바꾼다."""
    result: dict[str, float] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        symbol, value = item.split(":", 1)
        symbol = symbol.strip()
        value = value.strip()
        if not symbol or not value:
            continue
        result[symbol] = float(value)
    return result


def parse_bool(raw: str, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def build_market_entry(symbol: str) -> dict[str, str]:
    """BASE/QUOTE 심볼을 봇에서 쓰는 마켓 사전으로 바꾼다."""
    if "/" not in symbol:
        raise ValueError(f"심볼 형식이 잘못되었습니다: {symbol}")

    base, quote = symbol.split("/", 1)
    base = base.strip()
    quote = quote.strip()
    normalized_symbol = f"{base}/{quote}"
    return {
        "name": base,
        "symbol": normalized_symbol,
        "base": base,
        "quote": quote,
    }


def load_alt_symbols(exchange_name: str) -> list[str]:
    """거래소별 알트 봇 감시 심볼 목록을 읽는다."""
    load_dotenv()

    exchange_key = exchange_name.strip().lower()
    if exchange_key == "okx":
        return parse_symbol_list(
            os.getenv("OKX_ALT_SYMBOLS"),
            DEFAULT_OKX_ALT_SYMBOLS,
        )
    if exchange_key == "upbit":
        return parse_symbol_list(
            os.getenv("UPBIT_ALT_SYMBOLS"),
            DEFAULT_UPBIT_ALT_SYMBOLS,
        )
    raise ValueError(f"지원하지 않는 거래소입니다: {exchange_name}")


def load_alt_markets(exchange_name: str) -> list[dict[str, str]]:
    """거래소별 알트 봇 감시 심볼을 마켓 사전 목록으로 반환한다."""
    return [build_market_entry(symbol) for symbol in load_alt_symbols(exchange_name)]


def load_managed_symbols(exchange_name: str) -> list[str]:
    """거래소별 운영/분석 대상 심볼 목록을 읽는다."""
    load_dotenv()

    exchange_key = exchange_name.strip().lower()
    if exchange_key == "okx":
        default_symbols = [DEFAULT_OKX_BTC_SYMBOL, *load_alt_symbols("okx")]
        extra_symbols = parse_symbol_list(os.getenv("ANALYSIS_OKX_SYMBOLS"))
        return parse_symbol_list(None, [*default_symbols, *extra_symbols])
    if exchange_key == "upbit":
        default_symbols = [DEFAULT_UPBIT_BTC_SYMBOL, *load_alt_symbols("upbit")]
        extra_symbols = parse_symbol_list(os.getenv("ANALYSIS_UPBIT_SYMBOLS"))
        return parse_symbol_list(None, [*default_symbols, *extra_symbols])
    raise ValueError(f"지원하지 않는 거래소입니다: {exchange_name}")


def load_strategy_settings(
    min_buy_order_env_key: str, default_min_buy_order_value: float
) -> StrategySettings:
    """공통 전략 설정과 거래소별 최소 주문 금액 설정을 함께 읽는다."""
    load_dotenv()

    return StrategySettings(
        version=os.getenv("STRATEGY_VERSION", "alt_v1").strip(),
        buy_split_ratio=float(os.getenv("STRATEGY_BUY_SPLIT_RATIO", "0.10")),
        sell_split_ratio=float(os.getenv("STRATEGY_SELL_SPLIT_RATIO", "0.10")),
        max_entry_count=int(os.getenv("STRATEGY_MAX_ENTRY_COUNT", "3")),
        min_trade_interval_sec=int(
            os.getenv("STRATEGY_MIN_TRADE_INTERVAL_SEC", "300")
        ),
        enable_trend_follow_entry=parse_bool(
            os.getenv("STRATEGY_ENABLE_TREND_FOLLOW_ENTRY", "false"),
            default=False,
        ),
        trend_follow_requires_prev_above_ma=parse_bool(
            os.getenv("STRATEGY_TREND_FOLLOW_REQUIRE_PREV_ABOVE_MA", "true"),
            default=True,
        ),
        trend_follow_requires_price_rising=parse_bool(
            os.getenv("STRATEGY_TREND_FOLLOW_REQUIRE_PRICE_RISING", "true"),
            default=True,
        ),
        enable_higher_timeframe_filter=parse_bool(
            os.getenv("STRATEGY_ENABLE_HIGHER_TIMEFRAME_FILTER", "true"),
            default=True,
        ),
        higher_timeframe=os.getenv("STRATEGY_HIGHER_TIMEFRAME", "5m"),
        higher_timeframe_ma_period=int(
            os.getenv("STRATEGY_HIGHER_TIMEFRAME_MA_PERIOD", "20")
        ),
        enable_volume_filter=parse_bool(
            os.getenv("STRATEGY_ENABLE_VOLUME_FILTER", "true"),
            default=True,
        ),
        volume_lookback=int(os.getenv("STRATEGY_VOLUME_LOOKBACK", "20")),
        min_volume_ratio=float(os.getenv("STRATEGY_MIN_VOLUME_RATIO", "1.2")),
        min_volume_ratio_map=parse_symbol_float_map(
            os.getenv("STRATEGY_MIN_VOLUME_RATIO_MAP", "")
        ),
        enable_volatility_filter=parse_bool(
            os.getenv("STRATEGY_ENABLE_VOLATILITY_FILTER", "true"),
            default=True,
        ),
        volatility_lookback=int(os.getenv("STRATEGY_VOLATILITY_LOOKBACK", "20")),
        min_volatility_pct=float(
            os.getenv("STRATEGY_MIN_VOLATILITY_PCT", "0.05")
        ),
        max_volatility_pct=float(
            os.getenv("STRATEGY_MAX_VOLATILITY_PCT", "5.0")
        ),
        min_crossover_gap_pct=float(
            os.getenv("STRATEGY_MIN_CROSSOVER_GAP_PCT", "1.2")
        ),
        averaging_down_gap_pct=float(
            os.getenv("STRATEGY_AVERAGING_DOWN_GAP_PCT", "2.0")
        ),
        min_take_profit_pct=float(
            os.getenv("STRATEGY_MIN_TAKE_PROFIT_PCT", "1.0")
        ),
        stop_loss_pct=float(
            os.getenv("STRATEGY_STOP_LOSS_PCT", "1.5")
        ),
        min_buy_order_value=float(
            os.getenv(min_buy_order_env_key, str(default_min_buy_order_value))
        ),
        loop_interval_sec=int(os.getenv("STRATEGY_LOOP_INTERVAL_SEC", "10")),
        min_crossover_gap_pct_map=parse_symbol_float_map(
            os.getenv("STRATEGY_MIN_CROSSOVER_GAP_PCT_MAP", "")
        ),
        min_take_profit_pct_map=parse_symbol_float_map(
            os.getenv("STRATEGY_MIN_TAKE_PROFIT_PCT_MAP", "")
        ),
        stop_loss_pct_map=parse_symbol_float_map(
            os.getenv("STRATEGY_STOP_LOSS_PCT_MAP", "")
        ),
        min_order_amount_map=parse_symbol_float_map(
            os.getenv("STRATEGY_MIN_ORDER_AMOUNT_MAP", "")
        ),
        partial_take_profit_symbols=tuple(
            parse_symbol_list(os.getenv("STRATEGY_PARTIAL_TAKE_PROFIT_SYMBOLS"), [])
        ),
        partial_stop_loss_symbols=tuple(
            parse_symbol_list(os.getenv("STRATEGY_PARTIAL_STOP_LOSS_SYMBOLS"), [])
        ),
        partial_take_profit_ratio=float(
            os.getenv("STRATEGY_PARTIAL_TP_RATIO", "0.5")
        ),
        partial_stop_loss_ratio=float(
            os.getenv("STRATEGY_PARTIAL_SL_RATIO", "0.5")
        ),
    )
