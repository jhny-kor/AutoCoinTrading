"""
수정 요약
- 현재 실거래/분석 대상으로 등록하지 않은 거래소 심볼 후보를 찾아볼 수 있는 보조 도구를 추가

등록되지 않은 심볼 후보 조회 도구

- 거래소의 현물 마켓 목록을 읽고, 현재 .env 에 등록된 운영/분석 대상 심볼을 제외한 후보를 출력한다.
- 후보를 바로 분석 수집 대상으로 넣을 때 어떤 심볼이 비어 있는지 빠르게 확인하는 용도다.

사용 예시
- .venv/bin/python discover_untracked_symbols.py --exchange upbit --quote KRW
- .venv/bin/python discover_untracked_symbols.py --exchange okx --quote USDT --limit 50
"""

from __future__ import annotations

import argparse

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
    args = parser.parse_args()

    symbols = discover_symbols(args.exchange, args.quote.upper())
    managed = load_managed_symbols(args.exchange)

    print(f"거래소: {args.exchange}")
    print(f"기준 통화: {args.quote.upper()}")
    print(f"현재 등록된 운영/분석 심볼 수: {len(managed)}")
    print(f"등록되지 않은 후보 수: {len(symbols)}")
    print("-" * 60)

    for symbol in symbols[: args.limit]:
        print(symbol)


if __name__ == "__main__":
    main()
