"""
수정 요약
- 최근 N일 Sharpe 비슷한 점수로 미등록 심볼 후보를 정렬해 자동 후보 랭킹을 볼 수 있도록 확장

등록되지 않은 심볼 후보 조회 도구

- 거래소의 현물 마켓 목록을 읽고, 현재 .env 에 등록된 운영/분석 대상 심볼을 제외한 후보를 출력한다.
- 후보를 바로 분석 수집 대상으로 넣을 때 어떤 심볼이 비어 있는지 빠르게 확인하는 용도다.

사용 예시
- .venv/bin/python discover_untracked_symbols.py --exchange upbit --quote KRW
- .venv/bin/python discover_untracked_symbols.py --exchange okx --quote USDT --limit 50
"""

from __future__ import annotations

import argparse
import math

import ccxt

from strategy_settings import load_managed_symbols


def create_client(exchange_name: str) -> ccxt.Exchange:
    if exchange_name == "okx":
        return ccxt.okx(
            {
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    "fetchMarkets": ["spot"],
                },
            }
        )
    if exchange_name == "upbit":
        return ccxt.upbit(
            {
                "enableRateLimit": True,
                "options": {
                    "adjustForTimeDifference": True,
                },
            }
        )
    raise ValueError(f"지원하지 않는 거래소입니다: {exchange_name}")


def discover_symbols(exchange_name: str, quote: str) -> list[str]:
    exchange = create_client(exchange_name)
    markets = exchange.fetch_markets()
    managed = set(load_managed_symbols(exchange_name))

    candidates: list[str] = []
    for market in markets:
        if not market.get("spot"):
            continue
        symbol = str(market.get("symbol", "")).strip()
        if not symbol or symbol in managed:
            continue
        if not symbol.endswith(f"/{quote}"):
            continue
        candidates.append(symbol)

    return sorted(set(candidates))


def calc_sharpe_score_from_ohlcv(ohlcv: list[list[float]]) -> float | None:
    """일봉 종가 기준 단순 Sharpe 유사 점수를 계산한다."""
    if len(ohlcv) < 3:
        return None
    closes = [row[4] for row in ohlcv if len(row) > 4]
    if len(closes) < 3:
        return None
    returns: list[float] = []
    for prev_close, close in zip(closes, closes[1:]):
        if prev_close <= 0:
            continue
        returns.append((close - prev_close) / prev_close)
    if len(returns) < 2:
        return None
    mean_return = sum(returns) / len(returns)
    variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
    stddev = math.sqrt(variance)
    if stddev == 0:
        return None if mean_return <= 0 else 99.0
    return (mean_return / stddev) * math.sqrt(len(returns))


def fetch_candidate_ohlcv(exchange: ccxt.Exchange, symbol: str, days: int) -> list[list[float]]:
    """후보 심볼의 최근 일봉을 가져온다."""
    return exchange.fetch_ohlcv(symbol, timeframe="1d", limit=max(3, days + 1))


def discover_ranked_symbols(
    exchange_name: str,
    quote: str,
    *,
    lookback_days: int,
) -> list[tuple[str, float | None]]:
    """미등록 심볼 후보를 Sharpe 점수 기준으로 정렬한다."""
    exchange = create_client(exchange_name)
    markets = exchange.fetch_markets()
    managed = set(load_managed_symbols(exchange_name))

    ranked: list[tuple[str, float | None]] = []
    for market in markets:
        if not market.get("spot"):
            continue
        symbol = str(market.get("symbol", "")).strip()
        if not symbol or symbol in managed:
            continue
        if not symbol.endswith(f"/{quote}"):
            continue
        try:
            ohlcv = fetch_candidate_ohlcv(exchange, symbol, lookback_days)
            sharpe_score = calc_sharpe_score_from_ohlcv(ohlcv)
        except Exception:
            sharpe_score = None
        ranked.append((symbol, sharpe_score))

    def sort_key(item: tuple[str, float | None]) -> tuple[float, str]:
        symbol, score = item
        return (float("-inf") if score is None else score, symbol)

    return sorted(ranked, key=sort_key, reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="등록되지 않은 심볼 후보 조회")
    parser.add_argument(
        "--exchange",
        choices=["okx", "upbit"],
        required=True,
        help="조회할 거래소",
    )
    parser.add_argument(
        "--quote",
        required=True,
        help="기준 통화 (예: USDT, KRW)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="최대 출력 개수",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=14,
        help="Sharpe 계산에 사용할 최근 일수",
    )
    args = parser.parse_args()

    ranked_symbols = discover_ranked_symbols(
        args.exchange,
        args.quote.upper(),
        lookback_days=args.lookback_days,
    )
    managed = load_managed_symbols(args.exchange)

    print(f"거래소: {args.exchange}")
    print(f"기준 통화: {args.quote.upper()}")
    print(f"Sharpe 계산 기간: 최근 {args.lookback_days}일")
    print(f"현재 등록된 운영/분석 심볼 수: {len(managed)}")
    print(f"등록되지 않은 후보 수: {len(ranked_symbols)}")
    print("-" * 60)

    for symbol, sharpe_score in ranked_symbols[: args.limit]:
        sharpe_text = "-" if sharpe_score is None else f"{sharpe_score:.3f}"
        print(f"{symbol} | Sharpe {sharpe_text}")


if __name__ == "__main__":
    main()
