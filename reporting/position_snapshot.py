from __future__ import annotations

import json

import ccxt

from core.execution.okx import (
    create_okx_client,
    fetch_ohlcv_okx,
    get_spot_balances_okx,
    load_okx_config,
)
from core.execution.upbit import (
    create_upbit_client,
    fetch_ohlcv_upbit,
    get_spot_balances_upbit,
    load_upbit_config,
)
from log_path_utils import iter_files
from state_recovery import restore_program_position_states


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


def load_recovered_entry_prices(
    targets: tuple[tuple[str, list[str]], ...],
) -> dict[str, float]:
    """프로그램별 복구 상태에서 심볼별 평균 진입가를 모은다."""
    entry_prices: dict[str, float] = {}
    for program_name, symbols in targets:
        for symbol, state in restore_program_position_states(program_name, symbols).items():
            if state.average_entry_price is not None:
                entry_prices[symbol] = state.average_entry_price
    return entry_prices


def build_okx_positions_text(
    symbols: list[str],
    *,
    format_number,
) -> str:
    """OKX 현재 잔고와 포지션 요약을 만든다."""
    try:
        config = load_okx_config()
        exchange = create_okx_client(config)
        latest_entry_prices = load_latest_entry_prices()
        recovered_entry_prices = load_recovered_entry_prices(
            (
                ("ma_crossover_bot", [symbol for symbol in symbols if symbol != "BTC/USDT"]),
                ("okx_btc_ema_trend_bot", [symbol for symbol in symbols if symbol == "BTC/USDT"]),
            )
        )
        lines = ["[OKX]"]
        seen_quotes: set[str] = set()
        meaningful_position_count = 0

        for symbol in symbols:
            base, quote = symbol.split("/", 1)
            try:
                base_free, quote_free = get_spot_balances_okx(exchange, base, quote)
            except Exception as exc:
                lines.append(format_exchange_error_text("OKX", "잔고 조회", exc, symbol=symbol))
                continue

            if quote not in seen_quotes:
                lines.append(f"- 보유 {quote}: {format_number(quote_free, 4)}")
                seen_quotes.add(quote)

            try:
                ticker_ohlcv = fetch_ohlcv_okx(exchange, symbol, timeframe="1m", limit=1)
                last_close = ticker_ohlcv[-1][4]
            except Exception as exc:
                if base_free > 0:
                    lines.append(f"- {symbol}: {format_number(base_free, 6)} {base} | 현재가 조회 실패")
                lines.append(format_exchange_error_text("OKX", "현재가 조회", exc, symbol=symbol))
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


def build_upbit_positions_text(
    symbols: list[str],
    *,
    format_number,
) -> str:
    """업비트 현재 잔고와 포지션 요약을 만든다."""
    try:
        config = load_upbit_config()
        exchange = create_upbit_client(config)
        latest_entry_prices = load_latest_entry_prices()
        recovered_entry_prices = load_recovered_entry_prices(
            (
                ("upbit_ma_crossover_bot", [symbol for symbol in symbols if symbol != "BTC/KRW"]),
                ("upbit_btc_ema_trend_bot", [symbol for symbol in symbols if symbol == "BTC/KRW"]),
            )
        )
        lines = ["[UPBIT]"]
        seen_quotes: set[str] = set()
        meaningful_position_count = 0

        for symbol in symbols:
            base, quote = symbol.split("/", 1)
            try:
                base_free, quote_free = get_spot_balances_upbit(exchange, base, quote)
            except Exception as exc:
                lines.append(format_exchange_error_text("UPBIT", "잔고 조회", exc, symbol=symbol))
                continue

            if quote not in seen_quotes:
                lines.append(f"- 보유 {quote}: {format_number(quote_free, 0)}")
                seen_quotes.add(quote)

            try:
                ticker_ohlcv = fetch_ohlcv_upbit(exchange, symbol, timeframe="1m", limit=1)
                last_close = ticker_ohlcv[-1][4]
            except Exception as exc:
                if base_free > 0:
                    lines.append(f"- {symbol}: {format_number(base_free, 8)} {base} | 현재가 조회 실패")
                lines.append(format_exchange_error_text("UPBIT", "현재가 조회", exc, symbol=symbol))
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

