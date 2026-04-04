"""
수정 요약
- myAsset latest 가 부분 자산 이벤트만 담는 경우를 고려해 최근 myasset.jsonl 에서 통화별 최신 잔고를 보완 조회하고, 부족하면 REST fallback 으로 넘기도록 보강했다.
- latest/private/health JSON 이 부분 저장 상태여도 즉시 예외를 터뜨리지 않고 안전하게 None 으로 처리하도록 보강했다.
- 업비트 private 웹소켓 latest/jsonl 을 읽어 myAsset 잔고와 myOrder 최근 이벤트를 런타임에서 재사용할 수 있게 확장했다.
- 업비트 웹소켓 수집기가 저장한 최신 스냅샷과 1분 캔들 JSONL 을 읽어 전략 봇이 재사용할 수 있는 공용 provider 를 추가했다.
- stale 판정과 짧은 파일 캐시를 함께 제공해 phase 2/3/5 에서 best bid, 1분봉, 5분/15분 리샘플 캔들을 웹소켓 우선으로 읽을 수 있게 구성했다.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.market_data.upbit_market_state import symbol_to_upbit_market
from core.market_data.upbit_snapshot_store import sanitize_symbol_for_filename


class UpbitMarketDataProvider:
    """업비트 웹소켓 latest 스냅샷을 읽는 파일 기반 provider."""

    def __init__(
        self,
        root_dir: str | Path = "logs/runtime/upbit_ws",
        *,
        cache_ttl_sec: float = 0.25,
        stale_sec: float = 5.0,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.latest_dir = self.root_dir / "latest"
        self.candle_dir = self.root_dir / "candles_1m"
        self.private_dir = self.root_dir / "private"
        self.health_path = self.root_dir / "health.json"
        self.cache_ttl_sec = cache_ttl_sec
        self.stale_sec = stale_sec
        self._snapshot_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}
        self._health_cache: tuple[float, dict[str, Any] | None] = (0.0, None)
        self._ohlcv_cache: dict[tuple[str, str, int], tuple[float, list[list[float]]]] = {}
        self._private_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}

    def read_latest_snapshot(self, symbol: str) -> dict[str, Any] | None:
        """심볼별 최신 스냅샷을 읽는다."""
        now_ts = time.time()
        cached = self._snapshot_cache.get(symbol)
        if cached and (now_ts - cached[0]) <= self.cache_ttl_sec:
            return cached[1]

        path = self.latest_dir / f"{sanitize_symbol_for_filename(symbol)}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            payload = None
        self._snapshot_cache[symbol] = (now_ts, payload)
        return payload

    def read_health(self) -> dict[str, Any] | None:
        """수집기 health 상태를 읽는다."""
        now_ts = time.time()
        cached_ts, cached_payload = self._health_cache
        if (now_ts - cached_ts) <= self.cache_ttl_sec:
            return cached_payload

        try:
            payload = json.loads(self.health_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            payload = None
        self._health_cache = (now_ts, payload)
        return payload

    def read_private_latest(self, name: str) -> dict[str, Any] | None:
        """private latest JSON 을 읽는다."""
        now_ts = time.time()
        cached = self._private_cache.get(name)
        if cached and (now_ts - cached[0]) <= self.cache_ttl_sec:
            return cached[1]
        path = self.private_dir / f"{name}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            payload = None
        self._private_cache[name] = (now_ts, payload)
        return payload

    def is_symbol_fresh(self, symbol: str) -> bool:
        """심볼 스냅샷이 fresh 상태인지 반환한다."""
        snapshot = self.read_latest_snapshot(symbol)
        if not isinstance(snapshot, dict):
            return False
        orderbook = snapshot.get("orderbook")
        if not isinstance(orderbook, dict):
            return False
        timestamp_ms = orderbook.get("timestamp_ms") or snapshot.get("updated_at_ms")
        if timestamp_ms in (None, ""):
            return False
        age_sec = max(0.0, (time.time() * 1000 - float(timestamp_ms)) / 1000)
        if age_sec > self.stale_sec:
            return False

        health = self.read_health()
        if isinstance(health, dict) and health.get("connected") is False:
            return False
        return True

    def get_best_bid(self, symbol: str) -> float | None:
        """심볼의 최신 best bid 를 fresh 상태일 때만 반환한다."""
        if not self.is_symbol_fresh(symbol):
            return None
        snapshot = self.read_latest_snapshot(symbol)
        if not isinstance(snapshot, dict):
            return None
        orderbook = snapshot.get("orderbook")
        if not isinstance(orderbook, dict):
            return None
        value = orderbook.get("best_bid_price")
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def get_recent_ohlcv_1m(self, symbol: str, limit: int) -> list[list[float]] | None:
        """심볼의 최근 1분봉 OHLCV 를 반환한다."""
        if not self.is_symbol_fresh(symbol):
            return None

        cache_key = (symbol, "1m", limit)
        now_ts = time.time()
        cached = self._ohlcv_cache.get(cache_key)
        if cached and (now_ts - cached[0]) <= self.cache_ttl_sec:
            return cached[1]

        path = self.candle_dir / f"{sanitize_symbol_for_filename(symbol)}.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return None

        rows: list[list[float]] = []
        for line in lines[-limit:]:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            timestamp_ms = _coerce_candle_timestamp_ms(payload)
            opening_price = _to_float(payload.get("opening_price"))
            high_price = _to_float(payload.get("high_price"))
            low_price = _to_float(payload.get("low_price"))
            trade_price = _to_float(payload.get("trade_price"))
            volume = _to_float(payload.get("candle_acc_trade_volume"))
            if None in (timestamp_ms, opening_price, high_price, low_price, trade_price, volume):
                continue
            rows.append(
                [
                    int(timestamp_ms),
                    float(opening_price),
                    float(high_price),
                    float(low_price),
                    float(trade_price),
                    float(volume),
                ]
            )
        if len(rows) < limit:
            return None
        self._ohlcv_cache[cache_key] = (now_ts, rows)
        return rows

    def get_recent_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]] | None:
        """심볼의 최근 OHLCV 를 timeframe 기준으로 반환한다."""
        normalized = timeframe.strip().lower()
        if normalized == "1m":
            return self.get_recent_ohlcv_1m(symbol, limit)
        if not normalized.endswith("m"):
            return None
        try:
            target_minutes = int(normalized[:-1])
        except ValueError:
            return None
        if target_minutes <= 1:
            return self.get_recent_ohlcv_1m(symbol, limit)

        cache_key = (symbol, normalized, limit)
        now_ts = time.time()
        cached = self._ohlcv_cache.get(cache_key)
        if cached and (now_ts - cached[0]) <= self.cache_ttl_sec:
            return cached[1]

        source_limit = max(limit * target_minutes + 5, target_minutes * 3)
        source_rows = self.get_recent_ohlcv_1m(symbol, source_limit)
        if not source_rows or len(source_rows) < target_minutes:
            return None
        resampled = _resample_ohlcv_rows(source_rows, target_minutes)
        if len(resampled) < limit:
            return None
        result = resampled[-limit:]
        self._ohlcv_cache[cache_key] = (now_ts, result)
        return result

    def get_market_code(self, symbol: str) -> str:
        """프로젝트 심볼을 업비트 마켓 코드로 변환한다."""
        return symbol_to_upbit_market(symbol)

    def get_private_balances(self, base: str, quote: str) -> tuple[float, float] | None:
        """myAsset latest 에서 base/quote 잔고를 추정한다."""
        latest_payload = self.read_private_latest("myasset_latest")
        latest_by_currency = _extract_asset_balances_by_currency(latest_payload)

        base_free = latest_by_currency.get(base)
        quote_free = latest_by_currency.get(quote)

        if base_free is not None and quote_free is not None:
            return float(base_free), float(quote_free)

        path = self.private_dir / "myasset.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            lines = []

        seen: dict[str, float] = {}
        if base_free is not None:
            seen[base] = float(base_free)
        if quote_free is not None:
            seen[quote] = float(quote_free)

        for line in reversed(lines[-200:]):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            balances = _extract_asset_balances_by_currency(payload)
            for currency in (base, quote):
                if currency in seen:
                    continue
                balance = balances.get(currency)
                if balance is not None:
                    seen[currency] = float(balance)
            if base in seen and quote in seen:
                break

        if base in seen and quote in seen:
            return float(seen[base]), float(seen[quote])
        return None

    def find_recent_myorder_event(
        self,
        *,
        order_id: str,
        market: str | None = None,
        max_age_sec: float = 10.0,
        max_lines: int = 100,
    ) -> dict[str, Any] | None:
        """최근 myOrder 이벤트 중 주문 ID 가 일치하는 항목을 찾는다."""
        latest = self.read_private_latest("myorder_latest")
        for candidate in (latest,):
            if _matches_myorder_event(candidate, order_id=order_id, market=market, max_age_sec=max_age_sec):
                return candidate

        path = self.private_dir / "myorder.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return None
        for line in reversed(lines[-max_lines:]):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if _matches_myorder_event(payload, order_id=order_id, market=market, max_age_sec=max_age_sec):
                return payload
        return None


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_asset_balances_by_currency(payload: dict[str, Any] | None) -> dict[str, float]:
    """myAsset payload 에서 통화별 잔고를 추출한다."""
    if not isinstance(payload, dict):
        return {}

    candidates = payload.get("assets")
    if not isinstance(candidates, list):
        single_currency = payload.get("currency")
        if single_currency:
            candidates = [payload]
    if not isinstance(candidates, list):
        return {}

    balances: dict[str, float] = {}
    for item in candidates:
        if not isinstance(item, dict):
            continue
        currency = str(item.get("currency", "") or item.get("unit_currency", "") or "")
        balance = _to_float(item.get("balance"))
        if not currency or balance is None:
            continue
        balances[currency] = float(balance)
    return balances


def _coerce_candle_timestamp_ms(payload: dict[str, Any]) -> int | None:
    raw_timestamp = payload.get("timestamp_ms")
    if raw_timestamp not in (None, ""):
        try:
            return int(float(raw_timestamp))
        except (TypeError, ValueError):
            return None
    raw_kst = payload.get("candle_date_time_kst")
    if not raw_kst:
        return None
    try:
        from datetime import datetime
        return int(datetime.fromisoformat(f"{raw_kst}+09:00").timestamp() * 1000)
    except ValueError:
        return None


def _matches_myorder_event(
    payload: dict[str, Any] | None,
    *,
    order_id: str,
    market: str | None,
    max_age_sec: float,
) -> bool:
    if not isinstance(payload, dict):
        return False
    candidate_id = str(payload.get("uuid", "") or payload.get("id", "") or "")
    if not candidate_id or candidate_id != order_id:
        return False
    if market and str(payload.get("market", "") or "") not in {"", market}:
        return False
    captured_at = payload.get("captured_at_local")
    if not captured_at:
        return True
    try:
        from datetime import datetime
        age_sec = max(0.0, time.time() - datetime.fromisoformat(str(captured_at)).timestamp())
    except ValueError:
        return True
    return age_sec <= max_age_sec


def _resample_ohlcv_rows(rows: list[list[float]], target_minutes: int) -> list[list[float]]:
    """1분봉 rows 를 target_minutes 봉으로 리샘플링한다."""
    buckets: dict[int, list[list[float]]] = {}
    bucket_order: list[int] = []
    interval_ms = target_minutes * 60 * 1000
    for row in rows:
        timestamp_ms = int(row[0])
        bucket_ts = (timestamp_ms // interval_ms) * interval_ms
        if bucket_ts not in buckets:
            buckets[bucket_ts] = []
            bucket_order.append(bucket_ts)
        buckets[bucket_ts].append(row)

    result: list[list[float]] = []
    for bucket_ts in bucket_order:
        bucket_rows = buckets[bucket_ts]
        if not bucket_rows:
            continue
        opens = float(bucket_rows[0][1])
        highs = max(float(item[2]) for item in bucket_rows)
        lows = min(float(item[3]) for item in bucket_rows)
        closes = float(bucket_rows[-1][4])
        volume = sum(float(item[5]) for item in bucket_rows)
        result.append([bucket_ts, opens, highs, lows, closes, volume])
    return result
