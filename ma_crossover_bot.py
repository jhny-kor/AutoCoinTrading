"""
수정 요약
- 텔레그램 매수/매도 체결 알림에 실제 체결가와 체결 금액이 함께 보이도록 보강
- 부분 익절 직후 같은 코인 재진입과 추가 매수를 잠시 막는 전용 쿨다운을 추가
- 거래소 전체 기준 목표 비중과 남아 있는 누적 투입 원가를 바탕으로 알트 신규 매수 한도를 제한하는 포트폴리오 배분 로직을 추가
- 알트가 수수료를 제하고도 순익인 상태에서 메인 추세가 꺾이면 즉시 전량 익절하는 순익 보호 청산 규칙을 추가
- OKX 알트 체결 로그에 주문 ID, API 지연, 체결 비율, 슬리피지 같은 주문 실행 품질 지표를 함께 저장하도록 확장
- 심볼별 부분익절/부분손절 설정을 지원하고 ETH 같은 선택 알트에만 1회 부분청산을 적용하도록 확장
- OKX 알트 매도 체결 로그에도 왕복 수수료 추정 기반 순손익을 함께 남겨 /pnl 집계가 일관되도록 보강
- OKX 알트에서 최소 주문 수량 미만 잔량은 내부 포지션 상태도 함께 초기화해 재진입이 막히지 않도록 조정
- 알트 포지션의 최고가/최저가, MFE/MAE, 보유시간을 체결 로그에 함께 남겨 거래 품질 분석이 가능하도록 확장
- 알트 보수형 trend_follow_entry 를 추가해 연속 MA 상단 유지와 상승 확인 시 제한적으로 신규 진입을 허용
- 심볼별 거래량 기준을 읽어 PI 와 다른 알트 코인의 진입 품질 기준을 분리할 수 있게 개선
- OKX 알트 익절은 왕복 수수료보다 낮지 않도록 수수료 하한선을 적용하고, 전략 익절률은 더 빠르게 조정 가능하게 개선
- PI 먼지잔고는 포지션으로 보지 않도록 최소 주문 수량 기준으로 보유 여부를 판정하게 조정
- OKX 알트 감시 심볼 목록을 .env 기반 공통 로더로 읽도록 재구조화
- 공통 전략 값을 .env 에서 읽도록 구조 정리
- OKX 전용 값은 API 정보와 최소 주문 금액만 유지하도록 정리
- 낮은 시드머니 테스트 시 두 파일이 같은 전략 기준으로 동작하도록 맞춤
- 매수 신호는 빨간색, 매도 신호는 파란색으로 로그에 표시되도록 개선
- 실제 거래 발생 시 굵은 강조 배너 로그가 나오도록 개선
- 프로그램별 로그 파일이 자동으로 저장되도록 공통 로거 연결
- 심볼별 이격도 기준을 .env 에서 다르게 읽도록 개선
- 심볼별 익절률/손절률을 .env 에서 다르게 읽도록 개선
- 손실 한도 초과 시 데드크로스 없이도 즉시 청산하는 손절 규칙 추가
- 상위 타임프레임 추세와 같은 방향일 때만 신규 진입하는 필터 추가
- 일일 최대 손실 한도 도달 시 신규 매수를 중단하는 제한 추가
- 거래량 필터와 변동성 필터를 신규 진입 조건에 추가
- 텔레그램 알림 모듈 연결
- 매수/익절/손절/에러/일일 손실 제한 도달 시 텔레그램 메시지 전송 추가
- 체결 결과를 trade_logs/trade_history.jsonl 에 구조화해서 저장하도록 추가
- BTC 는 전용 EMA 봇으로 분리하고 기존 OKX 봇은 알트(PI) 전용으로 정리
- 전략 판단 로그를 system / strategy / trade JSONL 로 분리 저장하도록 추가
- 매수/매도 판단을 퍼널 단계와 reason 코드 기준으로 집계 가능하게 기록하도록 추가
- OKX 의 PI 최소 주문 수량 1개 규칙을 반영해 최소 수량 미만 주문을 차단하도록 추가
- 거래량 배수 계산을 형성 중인 현재 봉 대신 직전 마감 봉 기준으로 바꿔 더 안정적으로 해석하도록 조정
"""

import os
import time
import traceback
from datetime import datetime
from typing import Tuple

import ccxt
from dotenv import load_dotenv

from bot_logger import BLUE, RED, BotLogger
from portfolio_allocator import PortfolioAllocator
from structured_log_manager import FunnelStep, StructuredLogManager, choose_volatility_reason
from strategy_settings import load_alt_markets, load_managed_symbols, load_strategy_settings
from telegram_notifier import load_telegram_notifier
from trade_history_logger import (
    TradeHistoryLogger,
    estimate_round_trip_net_pnl,
    summarize_order_for_notification,
)

def load_config() -> dict:
    """환경 변수와 기본 설정 로드."""
    load_dotenv()

    api_key = os.getenv("OKX_API_KEY")
    api_secret = os.getenv("OKX_API_SECRET")
    api_passphrase = os.getenv("OKX_API_PASSPHRASE")

    if not api_key or not api_secret or not api_passphrase:
        raise RuntimeError(
            "OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE 가 .env 에 설정되어 있지 않습니다."
        )

    sandbox = os.getenv("OKX_SANDBOX", "true").lower() == "true"
    # OKX 전용 리스크 비율 (기본 5%)
    risk_per_trade = float(os.getenv("OKX_TRADE_RISK_PER_TRADE", "0.05"))
    fee_rate_pct = float(os.getenv("OKX_FEE_RATE_PCT", "1.0"))
    max_daily_loss_quote = float(os.getenv("OKX_MAX_DAILY_LOSS_QUOTE", "5.0"))

    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "api_passphrase": api_passphrase,
        "sandbox": sandbox,
        "risk_per_trade": risk_per_trade,
        "fee_rate_pct": fee_rate_pct,
        "max_daily_loss_quote": max_daily_loss_quote,
    }


def create_okx_client(config: dict) -> ccxt.okx:
    """OKX 클라이언트 생성 (테스트넷/실거래 모두 지원)."""
    exchange = ccxt.okx(
        {
            "apiKey": config["api_key"],
            "secret": config["api_secret"],
            "password": config["api_passphrase"],
            "enableRateLimit": True,
            "options": {
                # 현물만 사용하도록 명시
                "defaultType": "spot",
                # 일부 환경에서 OKX 마켓 전체를 불러오다 에러가 나는 이슈가 있어
                # fetchMarkets 대상을 spot 으로만 제한
                "fetchMarkets": ["spot"],
            },
        }
    )

    # 테스트넷 모드
    if config["sandbox"]:
        exchange.set_sandbox_mode(True)

    return exchange


def fetch_ohlcv(
    exchange: ccxt.okx, symbol: str, timeframe: str = "1m", limit: int = 200
):
    """
    과거 캔들 데이터를 가져온다.

    주의: 현재 ccxt + OKX 조합에서 load_markets() 중
    base/quote 가 None 이 되는 버그가 있어, 통합 fetch_ohlcv 대신
    OKX 원시(public) 캔들 API 를 직접 호출해서 사용한다.
    """
    # symbol "BTC/USDT" -> OKX instId "BTC-USDT" 로 변환
    inst_id = symbol.replace("/", "-")

    # ccxt 의 okx 래퍼가 제공하는 원시 public 엔드포인트 사용
    # https://www.okx.com/docs-v5/ko/#public-data-rest-api-get-candlesticks
    timeframe_map = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D",
    }
    bar = timeframe_map.get(timeframe, "1m")

    # OKX 는 최신 → 과거 순으로 내려오므로, ccxt ohlcv 포맷에 맞게 정렬
    res = exchange.publicGetMarketCandles(
        {
            "instId": inst_id,
            "bar": bar,
            "limit": limit,
        }
    )

    # res["data"] 형식:
    # [
    #   [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm, ...],
    #   ...
    # ]
    data = res.get("data", []) if isinstance(res, dict) else res
    ohlcv = []
    for item in data:
        ts = int(item[0])
        o = float(item[1])
        h = float(item[2])
        l = float(item[3])
        c = float(item[4])
        v = float(item[5])
        ohlcv.append([ts, o, h, l, c, v])

    # 오래된 → 최신 순으로 정렬
    ohlcv.sort(key=lambda x: x[0])
    return ohlcv


def calc_sma(prices, period: int) -> float:
    """단순 이동평균(SMA) 계산."""
    if len(prices) < period:
        raise ValueError("가격 데이터가 이동평균 기간보다 적습니다.")
    window = prices[-period:]
    return sum(window) / len(window)


def detect_crossover(
    closes, period: int
) -> Tuple[bool, bool, float, float, float, float]:
    """
    이동평균 돌파 여부 감지.

    returns:
        (bullish_cross, bearish_cross, prev_close, prev_ma, last_close, last_ma)
    """
    if len(closes) < period + 1:
        raise ValueError("이동평균 돌파를 계산하기 위한 캔들 수가 부족합니다.")

    prev_closes = closes[:-1]
    last_close = closes[-1]

    prev_ma = calc_sma(prev_closes, period)
    last_ma = calc_sma(closes, period)

    prev_close = prev_closes[-1]

    bullish = prev_close < prev_ma and last_close > last_ma
    bearish = prev_close > prev_ma and last_close < last_ma

    return bullish, bearish, prev_close, prev_ma, last_close, last_ma


def get_spot_balances(exchange: ccxt.okx, base: str, quote: str) -> Tuple[float, float]:
    """
    현물 지갑에서 base/quote 코인의 잔고를 가져온다.

    주의: ccxt 의 okx.fetch_balance() 는 내부에서 load_markets() 를 호출하면서
    앞서 본 것과 같은 base/quote NoneType 버그에 걸릴 수 있어,
    여기서는 OKX 계정 원시 API 를 직접 사용한다.
    """
    # https://www.okx.com/docs-v5/ko/#trading-account-rest-api-get-balance
    res = exchange.privateGetAccountBalance({})

    data = res.get("data", []) if isinstance(res, dict) else res
    if not data:
        return 0.0, 0.0

    details = data[0].get("details", [])
    base_free = 0.0
    quote_free = 0.0

    for d in details:
        ccy = d.get("ccy")
        avail = float(d.get("availBal", 0.0))
        if ccy == base:
            base_free = avail
        elif ccy == quote:
            quote_free = avail

    return float(base_free), float(quote_free)


def safe_amount_to_precision(exchange: ccxt.okx, symbol: str, amount: float) -> float:
    """
    amount_to_precision 을 시도하되, 마켓 정보가 로드되지 않은 경우
    단순 소수점 9자리까지 자르는 방식으로 폴백한다.
    """
    try:
        return float(exchange.amount_to_precision(symbol, amount))
    except Exception:
        # fallback: 대략적인 정규화 (거래소에서 추가로 거절/조정할 수 있음)
        return float(f"{amount:.9f}")


def calc_volume_ratio(ohlcv, lookback: int) -> float | None:
    """직전 마감 봉 거래량이 그 이전 평균 거래량의 몇 배인지 계산한다."""
    if len(ohlcv) < 3:
        return None
    completed = ohlcv[:-1]
    if len(completed) < 2:
        return None
    recent = (
        completed[-(lookback + 1):-1]
        if len(completed) >= lookback + 1
        else completed[:-1]
    )
    if not recent:
        return None
    avg_volume = sum(row[5] for row in recent) / len(recent)
    current_volume = completed[-1][5]
    if avg_volume <= 0:
        return None
    return current_volume / avg_volume


def calc_avg_abs_change_pct(closes, lookback: int) -> float | None:
    """최근 절대 등락률 평균을 계산한다."""
    if len(closes) < 2:
        return None
    recent_closes = closes[-(lookback + 1):] if len(closes) >= lookback + 1 else closes
    changes = []
    for prev, curr in zip(recent_closes, recent_closes[1:]):
        if prev == 0:
            continue
        changes.append(abs((curr - prev) / prev) * 100)
    if not changes:
        return None
    return sum(changes) / len(changes)


def place_market_order_okx(
    exchange: ccxt.okx, symbol: str, side: str, size: float, tgt_ccy: str | None = None
):
    """
    ccxt 의 create_order 가 load_markets() 를 내부에서 호출하면서
    base/quote NoneType 버그가 발생하므로, OKX 원시 주문 API 를 직접 호출한다.
    """
    inst_id = symbol.replace("/", "-")  # "BTC/USDT" -> "BTC-USDT"
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError("side 는 'buy' 또는 'sell' 이어야 합니다.")

    # 현물 계좌(tdMode='cash') 시장가 주문
    payload = {
        "instId": inst_id,
        "tdMode": "cash",
        "side": side,
        "ordType": "market",
        "sz": str(size),
    }
    if tgt_ccy is not None:
        payload["tgtCcy"] = tgt_ccy
    return exchange.privatePostTradeOrder(payload)


def run_bot():
    """
    단순 이동평균 돌파 전략 봇 메인 루프.

    - 심볼: .env 의 OKX_ALT_SYMBOLS 에 등록한 OKX 알트 현물
    - 타임프레임: 1분봉
    - 전략:
        - 이전 캔들에서는 가격 < MA, 현재 캔들에서 가격 > MA  -> 골든 크로스 -> 매수
        - 이전 캔들에서는 가격 > MA, 현재 캔들에서 가격 < MA  -> 데드 크로스 -> 매도
    """
    config = load_config()
    strategy = load_strategy_settings("OKX_MIN_BUY_ORDER_VALUE", 1.0)
    exchange = create_okx_client(config)

    # 심볼별 평균 진입가 저장 (손익 계산용)
    entry_price = {}
    # 심볼별 포지션 시작 시각 저장 (보유 시간 분석용)
    entry_opened_at = {}
    # 심볼별 진입 후 최고가/최저가 저장 (MFE/MAE 분석용)
    highest_price_since_entry = {}
    lowest_price_since_entry = {}
    # 심볼별 부분익절/부분손절 1회 실행 여부 저장
    partial_take_profit_done = {}
    partial_stop_loss_done = {}
    partial_take_profit_last_at = {}
    # 심볼별 분할 진입 횟수 저장
    entry_count = {}
    # 심볼별 마지막 거래 시각 저장 (과매매 방지용)
    last_trade_at = {}
    # 일일 누적 실현 손익(quote 기준)
    daily_realized_pnl_quote = 0.0
    daily_pnl_date = datetime.now().date()
    logger = BotLogger("ma_crossover_bot")
    structured_logger = StructuredLogManager("ma_crossover_bot")
    notifier = load_telegram_notifier()
    trade_history = TradeHistoryLogger()
    portfolio_allocator = PortfolioAllocator(
        exchange_name="OKX",
        quote_currency="USDT",
        tracked_symbols=load_managed_symbols("okx"),
    )
    daily_limit_notified = False

    # BTC 는 전용 EMA 봇으로 분리했으므로 기존 OKX 봇은 알트만 담당한다.
    markets = load_alt_markets("okx")

    timeframe = "1m"
    ma_period = 20

    log = logger.log

    log("=== OKX 단순 이동평균 돌파 봇 시작 ===")
    log(f"타임프레임: {timeframe}, MA 기간: {ma_period}")
    log(f"테스트넷 모드: {'ON' if config['sandbox'] else 'OFF'}")
    log(f"한 번에 사용하는 계좌 비율: {config['risk_per_trade']}")
    log(f"일일 최대 손실 제한: {config['max_daily_loss_quote']} USDT")
    structured_logger.log_system(
        level="INFO",
        event="bot_started",
        message="OKX 알트 전략 봇을 시작합니다.",
        context={
            "timeframe": timeframe,
            "ma_period": ma_period,
            "sandbox": config["sandbox"],
            "risk_per_trade": config["risk_per_trade"],
            "max_daily_loss_quote": config["max_daily_loss_quote"],
        },
    )

    while True:
        today = datetime.now().date()
        if today != daily_pnl_date:
            daily_pnl_date = today
            daily_realized_pnl_quote = 0.0
            daily_limit_notified = False
            log("일자가 변경되어 일일 손익 누적값을 초기화합니다.")
            structured_logger.log_system(
                level="INFO",
                event="daily_pnl_reset",
                message="일일 손익 누적값을 초기화했습니다.",
            )

        for m in markets:
            symbol = m["symbol"]
            base = m["base"]
            quote = m["quote"]

            log(f"=== {symbol} 체크 시작 ===")

            try:
                log("캔들 데이터 조회 시도 중...")
                ohlcv = fetch_ohlcv(
                    exchange, symbol, timeframe=timeframe, limit=ma_period + 5
                )
                closes = [c[4] for c in ohlcv]  # 종가 리스트
                log("이동평균 및 크로스 계산 중...")
                (
                    bullish,
                    bearish,
                    prev_close,
                    prev_ma,
                    last_close,
                    last_ma,
                ) = detect_crossover(closes, ma_period)

                log("-" * 60)
                log(f"[{symbol}] 이전 종가: {prev_close:.4f}, 이전 MA: {prev_ma:.4f}")
                log(f"[{symbol}] 현재 종가: {last_close:.4f}, 현재 MA: {last_ma:.4f}")
                logger.log_signal(symbol, bullish, bearish)
                log(
                    f"[{symbol}] 신호 상태: bullish(강세)={bullish}, bearish(약세)={bearish}"
                )
                gap_pct = abs(last_close - last_ma) / last_ma * 100 if last_ma else 0.0
                log(f"[{symbol}] 현재 종가와 MA 이격도: {gap_pct:.4f}%")

                volume_ratio = calc_volume_ratio(ohlcv, strategy.volume_lookback)
                effective_min_volume_ratio = strategy.get_min_volume_ratio(symbol)
                volume_filter_passed = True
                if strategy.enable_volume_filter and volume_ratio is not None:
                    volume_filter_passed = (
                        volume_ratio >= effective_min_volume_ratio
                    )
                    log(
                        f"[{symbol}] 거래량 배수: {volume_ratio:.4f}배 "
                        f"(기준 {effective_min_volume_ratio:.4f}배)"
                    )

                avg_abs_change_pct = calc_avg_abs_change_pct(
                    closes, strategy.volatility_lookback
                )
                volatility_filter_passed = True
                if strategy.enable_volatility_filter and avg_abs_change_pct is not None:
                    volatility_filter_passed = (
                        strategy.min_volatility_pct
                        <= avg_abs_change_pct
                        <= strategy.max_volatility_pct
                    )
                    log(
                        f"[{symbol}] 최근 평균 절대 변화율: {avg_abs_change_pct:.4f}% "
                        f"(허용 {strategy.min_volatility_pct:.4f}% ~ "
                        f"{strategy.max_volatility_pct:.4f}%)"
                    )

                htf_bullish = True
                htf_bearish = True
                if strategy.enable_higher_timeframe_filter:
                    log(
                        f"[{symbol}] 상위 타임프레임({strategy.higher_timeframe}) 추세 확인 중..."
                    )
                    htf_ohlcv = fetch_ohlcv(
                        exchange,
                        symbol,
                        timeframe=strategy.higher_timeframe,
                        limit=strategy.higher_timeframe_ma_period + 5,
                    )
                    htf_closes = [c[4] for c in htf_ohlcv]
                    htf_last_close = htf_closes[-1]
                    htf_last_ma = calc_sma(
                        htf_closes, strategy.higher_timeframe_ma_period
                    )
                    htf_bullish = htf_last_close > htf_last_ma
                    htf_bearish = htf_last_close < htf_last_ma
                    log(
                        f"[{symbol}] 상위 타임프레임 종가: {htf_last_close:.4f}, "
                        f"상위 MA: {htf_last_ma:.4f}, "
                        f"상승추세={htf_bullish}, 하락추세={htf_bearish}"
                    )

                log("잔고 조회 중...")
                base_free, quote_free = get_spot_balances(exchange, base, quote)
                log(f"현물 잔고 - {base}: {base_free}, {quote}: {quote_free}")

                min_order_amount = strategy.get_min_order_amount(symbol)
                position_threshold = min_order_amount if min_order_amount > 0 else 0.0001
                # 거래 가능한 최소 수량보다 작은 잔고는 먼지잔고로 보고 포지션에서 제외
                has_position = base_free >= position_threshold
                avg_entry_price = entry_price.get(symbol)
                if has_position and avg_entry_price is None:
                    # 재시작 후 기존 보유분의 실제 진입가를 알 수 없으므로 현재가를 임시 기준으로 사용
                    entry_price[symbol] = last_close
                    avg_entry_price = last_close
                    entry_count[symbol] = max(entry_count.get(symbol, 0), 1)
                    entry_opened_at[symbol] = entry_opened_at.get(symbol, time.time())
                    highest_price_since_entry[symbol] = last_close
                    lowest_price_since_entry[symbol] = last_close
                    log(
                        f"[{symbol}] 기존 보유 물량이 감지되어 평균 진입가를 현재가({last_close:.4f})로 임시 설정합니다."
                    )
                    structured_logger.log_system(
                        level="INFO",
                        event="position_bootstrap",
                        message="기존 보유 포지션을 감지해 평균 진입가를 임시 설정했습니다.",
                        symbol=symbol,
                        context={"bootstrap_entry_price": last_close},
                    )
                elif not has_position:
                    # 최소 주문 수량 미만 잔량은 신규 포지션으로 다시 진입할 수 있도록 내부 상태를 비운다.
                    if (
                        symbol in entry_price
                        or symbol in entry_count
                        or symbol in entry_opened_at
                    ):
                        entry_price.pop(symbol, None)
                        entry_count.pop(symbol, None)
                        entry_opened_at.pop(symbol, None)
                        highest_price_since_entry.pop(symbol, None)
                        lowest_price_since_entry.pop(symbol, None)
                        partial_take_profit_done.pop(symbol, None)
                        partial_stop_loss_done.pop(symbol, None)
                        log(
                            f"[{symbol}] 최소 주문 수량 미만 잔량은 포지션에서 제외하고 재진입 가능 상태로 초기화합니다."
                        )

                current_entry_count = entry_count.get(symbol, 0)
                last_trade_ts = last_trade_at.get(symbol, 0.0)
                seconds_since_last_trade = time.time() - last_trade_ts
                in_cooldown = (
                    seconds_since_last_trade < strategy.min_trade_interval_sec
                )
                partial_take_profit_last_ts = partial_take_profit_last_at.get(symbol, 0.0)
                partial_take_profit_cooldown_remaining = max(
                    0.0,
                    strategy.partial_take_profit_reentry_cooldown_sec
                    - (time.time() - partial_take_profit_last_ts),
                ) if partial_take_profit_last_ts > 0 else 0.0
                partial_take_profit_cooldown_active = (
                    partial_take_profit_cooldown_remaining > 0
                )

                if in_cooldown:
                    remain_sec = int(
                        strategy.min_trade_interval_sec - seconds_since_last_trade
                    )
                    log(
                        f"[{symbol}] 최근 거래 후 쿨다운 중입니다. 남은 시간: {remain_sec}초"
                    )
                if partial_take_profit_cooldown_active:
                    log(
                        f"[{symbol}] 부분 익절 후 재진입/추가매수 쿨다운 중입니다. "
                        f"남은 시간: {int(partial_take_profit_cooldown_remaining)}초"
                    )

                min_gap_pct = strategy.get_crossover_gap_pct(symbol)
                position_ratio = strategy.get_position_ratio(
                    symbol,
                    config["risk_per_trade"],
                )
                signal_is_strong = gap_pct >= min_gap_pct
                trend_follow_entry = (
                    strategy.enable_trend_follow_entry
                    and last_close > last_ma
                    and (
                        not strategy.trend_follow_requires_prev_above_ma
                        or prev_close > prev_ma
                    )
                    and (
                        not strategy.trend_follow_requires_price_rising
                        or last_close > prev_close
                    )
                )
                entry_signal = bullish or trend_follow_entry
                dynamic_bonus_eligible = (
                    not has_position
                    and bullish
                    and (
                        not portfolio_allocator.settings.dynamic_require_strong_signal
                        or signal_is_strong
                    )
                    and (
                        volume_ratio is not None
                        and volume_ratio >= portfolio_allocator.settings.dynamic_volume_ratio_threshold
                    )
                    and (
                        not portfolio_allocator.settings.dynamic_require_trend_ok
                        or htf_bullish
                    )
                )
                requested_order_value = (
                    quote_free * position_ratio * strategy.buy_split_ratio
                )
                allocation_decision = portfolio_allocator.build_buy_decision(
                    exchange=exchange,
                    symbol=symbol,
                    requested_order_value_quote=requested_order_value,
                    dynamic_bonus_eligible=dynamic_bonus_eligible,
                )
                usdt_to_use = allocation_decision.approved_order_value_quote
                estimated_buy_amount = usdt_to_use / last_close if last_close else 0.0
                log(f"[{symbol}] 적용 이격도 기준: {min_gap_pct:.4f}%")
                log(f"[{symbol}] 적용 매수 비중: {position_ratio:.4f}")
                log(
                    f"[{symbol}] 포트폴리오 목표 비중: 기본 {allocation_decision.base_target_pct * 100:.2f}% | "
                    f"유효 {allocation_decision.effective_target_pct * 100:.2f}% | "
                    f"누적 투입 {allocation_decision.current_cost_basis_quote:.4f} {quote} | "
                    f"남은 예산 {allocation_decision.remaining_budget_quote:.4f} {quote}"
                )
                if allocation_decision.dynamic_bonus_applied:
                    log(
                        f"[{symbol}] 거래량/추세 강세로 목표 비중을 "
                        f"+{allocation_decision.dynamic_bonus_pct * 100:.2f}% 임시 확대합니다."
                    )
                if min_order_amount > 0:
                    log(f"[{symbol}] 적용 최소 주문 수량: {min_order_amount:.4f} {base}")
                    log(f"[{symbol}] 포지션 인식 최소 수량도 동일하게 {position_threshold:.4f} {base} 로 적용합니다.")
                if (entry_signal or bearish) and not signal_is_strong:
                    log(
                        f"[{symbol}] 신호가 약합니다. 수수료(거래당 1%)를 고려해 이번 신호는 건너뜁니다."
                    )
                if trend_follow_entry and not bullish:
                    log(
                        f"[{symbol}] 신규 골든크로스는 아니지만 MA 상단 유지 추세 조건으로 진입 후보를 허용합니다."
                    )

                if (
                    strategy.enable_higher_timeframe_filter
                    and entry_signal
                    and not htf_bullish
                ):
                    log(
                        f"[{symbol}] 상위 타임프레임 상승 추세가 아니어서 매수를 보류합니다."
                    )
                if (
                    strategy.enable_higher_timeframe_filter
                    and bearish
                    and not htf_bearish
                ):
                    log(
                        f"[{symbol}] 상위 타임프레임 하락 추세가 아니어서 일반 매도를 보류합니다."
                    )
                if entry_signal and strategy.enable_volume_filter and not volume_filter_passed:
                    log(
                        f"[{symbol}] 거래량이 부족하여 신규 매수를 보류합니다."
                    )
                if entry_signal and strategy.enable_volatility_filter and not volatility_filter_passed:
                    log(
                        f"[{symbol}] 변동성이 기준 범위를 벗어나 신규 매수를 보류합니다."
                    )
                if (
                    entry_signal
                    and min_order_amount > 0
                    and estimated_buy_amount < min_order_amount
                ):
                    log(
                        f"[{symbol}] 추정 매수 수량 {estimated_buy_amount:.4f} {base} 가 "
                        f"거래소 최소 주문 수량 {min_order_amount:.4f} {base} 보다 작아 매수를 보류합니다."
                    )

                can_average_down = (
                    not has_position
                    or avg_entry_price is None
                    or last_close
                    <= avg_entry_price
                    * (1 - strategy.averaging_down_gap_pct / 100)
                )
                if entry_signal and has_position and not can_average_down:
                    log(
                        f"[{symbol}] 추가 매수 조건 미충족: 현재가가 평균 진입가보다 "
                        f"{strategy.averaging_down_gap_pct}% 이상 낮지 않습니다."
                    )

                pnl_pct = None
                current_net_realized_pnl_quote = None
                current_net_realized_pnl_pct = None
                mfe_pct = None
                mae_pct = None
                if has_position and avg_entry_price:
                    highest_price_since_entry[symbol] = max(
                        highest_price_since_entry.get(symbol, last_close),
                        last_close,
                    )
                    lowest_price_since_entry[symbol] = min(
                        lowest_price_since_entry.get(symbol, last_close),
                        last_close,
                    )
                    pnl_pct = (last_close - avg_entry_price) / avg_entry_price * 100
                    mfe_pct = (
                        (highest_price_since_entry[symbol] - avg_entry_price)
                        / avg_entry_price
                        * 100
                    )
                    mae_pct = (
                        (lowest_price_since_entry[symbol] - avg_entry_price)
                        / avg_entry_price
                        * 100
                    )
                    log(f"[{symbol}] 평균 진입가 대비 현재 수익률: {pnl_pct:.2f}%")
                elif not has_position:
                    highest_price_since_entry.pop(symbol, None)
                    lowest_price_since_entry.pop(symbol, None)

                fee_round_trip_pct = config["fee_rate_pct"] * 2
                effective_min_take_profit_pct = fee_round_trip_pct * 1.1
                take_profit_pct = strategy.get_take_profit_pct(symbol)
                stop_loss_pct = strategy.get_stop_loss_pct(symbol)
                partial_take_profit_enabled = strategy.uses_partial_take_profit(symbol)
                partial_stop_loss_enabled = strategy.uses_partial_stop_loss(symbol)
                partial_take_profit_pending = (
                    partial_take_profit_enabled
                    and not partial_take_profit_done.get(symbol, False)
                )
                partial_stop_loss_pending = (
                    partial_stop_loss_enabled
                    and not partial_stop_loss_done.get(symbol, False)
                )
                effective_take_profit_pct = max(
                    take_profit_pct,
                    effective_min_take_profit_pct,
                )
                if has_position and avg_entry_price:
                    (
                        _current_fee_quote_estimate,
                        current_net_realized_pnl_quote,
                        current_net_realized_pnl_pct,
                    ) = estimate_round_trip_net_pnl(
                        entry_price=avg_entry_price,
                        exit_price=last_close,
                        amount=base_free,
                        fee_rate_pct=config["fee_rate_pct"],
                    )
                if has_position:
                    log(
                        f"[{symbol}] 적용 익절률: {effective_take_profit_pct:.2f}% "
                        f"(전략값 {take_profit_pct:.2f}%, 왕복 수수료 {fee_round_trip_pct:.2f}%), "
                        f"적용 손절률: {stop_loss_pct:.2f}%"
                    )
                    if current_net_realized_pnl_pct is not None:
                        log(
                            f"[{symbol}] 수수료 반영 예상 순익률: {current_net_realized_pnl_pct:.2f}% "
                            f"(보호 익절 기준 {strategy.fee_protect_min_net_pnl_pct:.2f}%)"
                        )
                daily_loss_limit_reached = (
                    daily_realized_pnl_quote <= -config["max_daily_loss_quote"]
                )
                log(
                    f"[{symbol}] 오늘 누적 실현 손익: {daily_realized_pnl_quote:.4f} {quote}"
                )
                if daily_loss_limit_reached:
                    log(
                        f"[{symbol}] 일일 최대 손실 제한에 도달하여 신규 매수를 중단합니다."
                    )
                    if not daily_limit_notified:
                        notifier.notify_daily_loss_limit(
                            "OKX",
                            f"오늘 누적 실현 손익: {daily_realized_pnl_quote:.4f} {quote}\n"
                            f"손실 제한: -{config['max_daily_loss_quote']:.4f} {quote}",
                        )
                        daily_limit_notified = True

                take_profit_ready = (
                    pnl_pct is not None
                    and pnl_pct >= effective_take_profit_pct
                )
                stop_loss_triggered = (
                    pnl_pct is not None
                    and pnl_pct <= -stop_loss_pct
                )
                profit_protect_triggered = (
                    has_position
                    and strategy.enable_fee_protect_exit
                    and current_net_realized_pnl_pct is not None
                    and current_net_realized_pnl_pct >= strategy.fee_protect_min_net_pnl_pct
                    and bearish
                    and not stop_loss_triggered
                )
                estimated_sell_amount = (
                    base_free
                    if (stop_loss_triggered or profit_protect_triggered)
                    else (base_free * strategy.sell_split_ratio)
                )
                estimated_sell_amount = safe_amount_to_precision(
                    exchange, symbol, estimated_sell_amount
                )
                if (
                    bearish
                    and has_position
                    and pnl_pct is not None
                    and not take_profit_ready
                    and not profit_protect_triggered
                    and not stop_loss_triggered
                ):
                    log(
                        f"[{symbol}] 최소 익절률({effective_take_profit_pct:.2f}%) 미달로 매도를 보류합니다."
                    )
                if has_position and profit_protect_triggered:
                    log(
                        f"[{symbol}] 순익 보호 익절 조건 충족: 수수료 반영 순익률 "
                        f"{current_net_realized_pnl_pct:.2f}% >= {strategy.fee_protect_min_net_pnl_pct:.2f}%"
                    )
                if has_position and stop_loss_triggered:
                    log(
                        f"[{symbol}] 손절 조건 충족: 현재 수익률 {pnl_pct:.2f}% <= -{stop_loss_pct:.2f}%"
                    )
                if (
                    has_position
                    and (stop_loss_triggered or profit_protect_triggered or bearish)
                    and min_order_amount > 0
                    and 0 < estimated_sell_amount < min_order_amount
                ):
                    log(
                        f"[{symbol}] 추정 매도 수량 {estimated_sell_amount:.4f} {base} 가 "
                        f"거래소 최소 주문 수량 {min_order_amount:.4f} {base} 보다 작아 매도를 보류합니다."
                    )

                common_metrics = {
                    "strategy_name": "okx_alt_ma_crossover",
                    "strategy_version": strategy.version,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "ma_period": ma_period,
                    "price": last_close,
                    "ma": last_ma,
                    "gap_pct": gap_pct,
                    "trend_follow_entry": trend_follow_entry,
                    "volume_ratio": volume_ratio,
                    "avg_abs_change_pct": avg_abs_change_pct,
                    "htf_bullish": htf_bullish,
                    "htf_bearish": htf_bearish,
                    "base_free": base_free,
                    "quote_free": quote_free,
                    "position_ratio": position_ratio,
                    "has_position": has_position,
                    "position_threshold": position_threshold,
                    "entry_count": current_entry_count,
                    "pnl_pct": pnl_pct,
                    "portfolio_base_target_pct": allocation_decision.base_target_pct * 100,
                    "portfolio_effective_target_pct": allocation_decision.effective_target_pct * 100,
                    "portfolio_dynamic_bonus_pct": allocation_decision.dynamic_bonus_pct * 100,
                    "portfolio_dynamic_bonus_applied": allocation_decision.dynamic_bonus_applied,
                    "portfolio_total_budget_quote": allocation_decision.total_portfolio_quote,
                    "portfolio_current_cost_basis_quote": allocation_decision.current_cost_basis_quote,
                    "portfolio_remaining_budget_quote": allocation_decision.remaining_budget_quote,
                    "net_pnl_pct_estimate": current_net_realized_pnl_pct,
                    "fee_protect_min_net_pnl_pct": strategy.fee_protect_min_net_pnl_pct,
                    "daily_realized_pnl_quote": daily_realized_pnl_quote,
                    "profit_protect_triggered": profit_protect_triggered,
                    "partial_take_profit_cooldown_active": partial_take_profit_cooldown_active,
                    "partial_take_profit_cooldown_remaining_sec": partial_take_profit_cooldown_remaining,
                    "partial_take_profit_pending": partial_take_profit_pending,
                    "partial_stop_loss_pending": partial_stop_loss_pending,
                }

                entry_steps = [
                    FunnelStep(
                        stage="trend",
                        passed=entry_signal,
                        reason="no_entry_signal",
                        actual={
                            "bullish_signal": bullish,
                            "trend_follow_entry": trend_follow_entry,
                        },
                        required={"bullish_or_trend_follow_entry": True},
                    ),
                    FunnelStep(
                        stage="distance",
                        passed=signal_is_strong,
                        reason="distance_too_small",
                        actual={"gap_pct": gap_pct},
                        required={"min_gap_pct": min_gap_pct},
                    ),
                    FunnelStep(
                        stage="higher_timeframe",
                        passed=(
                            not strategy.enable_higher_timeframe_filter or htf_bullish
                        ),
                        reason="higher_timeframe_not_bullish",
                        actual={"htf_bullish": htf_bullish},
                        required={"htf_bullish": True},
                    ),
                    FunnelStep(
                        stage="volume",
                        passed=(
                            not strategy.enable_volume_filter or volume_filter_passed
                        ),
                        reason="volume_low",
                        actual={"volume_ratio": volume_ratio},
                        required={"min_volume_ratio": effective_min_volume_ratio},
                    ),
                    FunnelStep(
                        stage="volatility",
                        passed=(
                            not strategy.enable_volatility_filter
                            or volatility_filter_passed
                        ),
                        reason=choose_volatility_reason(
                            avg_abs_change_pct,
                            min_value=strategy.min_volatility_pct,
                            max_value=strategy.max_volatility_pct,
                        ),
                        actual={"avg_abs_change_pct": avg_abs_change_pct},
                        required={
                            "min_volatility_pct": strategy.min_volatility_pct,
                            "max_volatility_pct": strategy.max_volatility_pct,
                        },
                    ),
                    FunnelStep(
                        stage="partial_take_profit_cooldown",
                        passed=not partial_take_profit_cooldown_active,
                        reason="partial_take_profit_cooldown_active",
                        actual={
                            "cooldown_remaining_sec": partial_take_profit_cooldown_remaining
                        },
                        required={"cooldown_inactive": True},
                    ),
                    FunnelStep(
                        stage="cooldown",
                        passed=not in_cooldown,
                        reason="cooldown_active",
                        actual={"seconds_since_last_trade": seconds_since_last_trade},
                        required={
                            "min_trade_interval_sec": strategy.min_trade_interval_sec
                        },
                    ),
                    FunnelStep(
                        stage="position_rule",
                        passed=can_average_down,
                        reason="avg_price_rule_block",
                        actual={
                            "last_close": last_close,
                            "avg_entry_price": avg_entry_price,
                        },
                        required={
                            "required_price_lte": (
                                None
                                if avg_entry_price is None
                                else avg_entry_price
                                * (1 - strategy.averaging_down_gap_pct / 100)
                            )
                        },
                    ),
                    FunnelStep(
                        stage="entry_limit",
                        passed=current_entry_count < strategy.max_entry_count,
                        reason="max_entry_reached",
                        actual={"entry_count": current_entry_count},
                        required={"max_entry_count": strategy.max_entry_count},
                    ),
                    FunnelStep(
                        stage="risk_limit",
                        passed=not daily_loss_limit_reached,
                        reason="daily_loss_limit_reached",
                        actual={
                            "daily_realized_pnl_quote": daily_realized_pnl_quote
                        },
                        required={
                            "min_daily_realized_pnl_quote": -config["max_daily_loss_quote"]
                        },
                    ),
                    FunnelStep(
                        stage="portfolio_budget",
                        passed=allocation_decision.remaining_budget_quote > 0,
                        reason="portfolio_budget_exhausted",
                        actual={
                            "current_cost_basis_quote": allocation_decision.current_cost_basis_quote,
                            "remaining_budget_quote": allocation_decision.remaining_budget_quote,
                        },
                        required={
                            "portfolio_target_budget_quote": allocation_decision.target_budget_quote,
                        },
                    ),
                    FunnelStep(
                        stage="order_value",
                        passed=usdt_to_use > strategy.min_buy_order_value,
                        reason="order_value_too_small",
                        actual={"order_value_quote": usdt_to_use},
                        required={
                            "min_buy_order_value": strategy.min_buy_order_value
                        },
                    ),
                    FunnelStep(
                        stage="order_amount",
                        passed=(
                            min_order_amount <= 0
                            or estimated_buy_amount >= min_order_amount
                        ),
                        reason="order_amount_too_small",
                        actual={"estimated_buy_amount": estimated_buy_amount},
                        required={"min_order_amount": min_order_amount},
                    ),
                ]
                entry_ready, _ = structured_logger.run_funnel(
                    symbol=symbol,
                    side="entry",
                    steps=entry_steps,
                    metrics=common_metrics,
                    ready_stage="buy_ready",
                    ready_reason="entry_conditions_met",
                )

                exit_steps = [
                    FunnelStep(
                        stage="position",
                        passed=has_position,
                        reason="no_position",
                        actual={"has_position": has_position},
                        required={"has_position": True},
                    ),
                    FunnelStep(
                        stage="exit_trigger",
                        passed=(stop_loss_triggered or profit_protect_triggered or bearish),
                        reason="no_exit_signal",
                        actual={
                            "stop_loss_triggered": stop_loss_triggered,
                            "profit_protect_triggered": profit_protect_triggered,
                            "bearish_signal": bearish,
                        },
                        required={
                            "stop_loss_triggered_or_profit_protect_or_bearish_signal": True
                        },
                    ),
                    FunnelStep(
                        stage="cooldown",
                        passed=(stop_loss_triggered or profit_protect_triggered or not in_cooldown),
                        reason="cooldown_active",
                        actual={"seconds_since_last_trade": seconds_since_last_trade},
                        required={
                            "min_trade_interval_sec": strategy.min_trade_interval_sec
                        },
                    ),
                    FunnelStep(
                        stage="distance",
                        passed=(stop_loss_triggered or profit_protect_triggered or signal_is_strong),
                        reason="distance_too_small",
                        actual={"gap_pct": gap_pct},
                        required={"min_gap_pct": min_gap_pct},
                    ),
                    FunnelStep(
                        stage="higher_timeframe",
                        passed=(
                            stop_loss_triggered
                            or profit_protect_triggered
                            or not strategy.enable_higher_timeframe_filter
                            or htf_bearish
                        ),
                        reason="higher_timeframe_not_bearish",
                        actual={"htf_bearish": htf_bearish},
                        required={"htf_bearish": True},
                    ),
                    FunnelStep(
                        stage="take_profit",
                        passed=(stop_loss_triggered or profit_protect_triggered or take_profit_ready),
                        reason="take_profit_not_reached",
                        actual={
                            "pnl_pct": pnl_pct,
                            "net_pnl_pct_estimate": current_net_realized_pnl_pct,
                        },
                        required={
                            "min_take_profit_pct": effective_take_profit_pct,
                            "fee_protect_min_net_pnl_pct": strategy.fee_protect_min_net_pnl_pct,
                        },
                    ),
                    FunnelStep(
                        stage="amount",
                        passed=(
                            estimated_sell_amount > 0
                            and (
                                min_order_amount <= 0
                                or estimated_sell_amount >= min_order_amount
                            )
                        ),
                        reason=(
                            "order_amount_too_small"
                            if estimated_sell_amount > 0 and min_order_amount > 0
                            else "sell_amount_too_small"
                        ),
                        actual={"sell_amount": estimated_sell_amount},
                        required={
                            "sell_amount_gt": 0,
                            "min_order_amount": min_order_amount,
                        },
                    ),
                ]
                exit_ready, _ = structured_logger.run_funnel(
                    symbol=symbol,
                    side="exit",
                    steps=exit_steps,
                    metrics=common_metrics,
                    ready_stage="sell_ready",
                    ready_reason=(
                        "stop_loss_triggered"
                        if stop_loss_triggered
                        else "profit_protect_triggered"
                        if profit_protect_triggered
                        else "take_profit_conditions_met"
                    ),
                )

                # 매수 신호 발생 시, 분할 횟수/쿨다운/추가 매수 가격 조건을 모두 만족하면 진입
                if entry_ready:
                    if usdt_to_use <= strategy.min_buy_order_value:
                        log(
                            f"[{symbol}] 주문 금액이 {strategy.min_buy_order_value} {quote} 이하라 매수 주문을 생략합니다."
                        )
                    else:
                        order_value = float(f"{usdt_to_use:.8f}")
                        structured_logger.log_strategy(
                            symbol=symbol,
                            side="entry",
                            stage="order_requested",
                            result="requested",
                            reason="market_buy_requested",
                            actual={"order_value_quote": order_value},
                            metrics=common_metrics,
                        )
                        log(
                            f"[매수] 시장가 매수 시도: {symbol}, 사용 금액={order_value} {quote}"
                        )
                        order_request_started_at = time.time()
                        try:
                            order = place_market_order_okx(
                                exchange,
                                symbol,
                                "buy",
                                order_value,
                                tgt_ccy="quote_ccy",
                            )
                        except Exception as order_error:
                            structured_logger.log_strategy(
                                symbol=symbol,
                                side="entry",
                                stage="filled",
                                result="error",
                                reason="order_failed",
                                actual={"order_value_quote": order_value},
                                metrics=common_metrics,
                                extra={"error": repr(order_error)},
                            )
                            structured_logger.log_system(
                                level="WARNING",
                                event="order_failed",
                                message="매수 주문 요청이 실패했습니다.",
                                symbol=symbol,
                                context={
                                    "side": "buy",
                                    "order_value_quote": order_value,
                                    "error": repr(order_error),
                                },
                            )
                            raise
                        order_response_received_at = time.time()
                        # 시장가 체결가는 응답 시점에 바로 확정되지 않을 수 있어 현재가로 평균 진입가를 추정
                        estimated_bought_amount = order_value / last_close
                        if has_position and avg_entry_price and base_free > 0:
                            total_cost = (avg_entry_price * base_free) + (
                                last_close * estimated_bought_amount
                            )
                            total_size = base_free + estimated_bought_amount
                            entry_price[symbol] = total_cost / total_size
                        else:
                            entry_price[symbol] = last_close
                        entry_count[symbol] = current_entry_count + 1
                        if not has_position:
                            entry_opened_at[symbol] = time.time()
                        highest_price_since_entry[symbol] = max(
                            highest_price_since_entry.get(symbol, last_close),
                            last_close,
                        )
                        lowest_price_since_entry[symbol] = min(
                            lowest_price_since_entry.get(symbol, last_close),
                            last_close,
                        )
                        last_trade_at[symbol] = time.time()
                        structured_logger.log_strategy(
                            symbol=symbol,
                            side="entry",
                            stage="filled",
                            result="filled",
                            reason="buy_filled",
                            actual={
                                "filled_amount": estimated_bought_amount,
                                "order_value_quote": order_value,
                            },
                            metrics={
                                **common_metrics,
                                "estimated_entry_price_after": entry_price[symbol],
                            },
                        )
                        structured_logger.log_trade_event(
                            symbol=symbol,
                            side="buy",
                            reason="entry",
                            result="filled",
                            actual={
                                "filled_amount": estimated_bought_amount,
                                "order_value_quote": order_value,
                            },
                            metrics={
                                **common_metrics,
                                "estimated_entry_price_after": entry_price[symbol],
                            },
                        )
                        logger.log_trade_banner(
                            RED,
                            f"[{symbol}] 매수 주문 체결",
                            f"주문 결과: {order}",
                        )
                        buy_summary = summarize_order_for_notification(
                            raw_order=order,
                            side="buy",
                            requested_amount=estimated_bought_amount,
                            requested_order_value_quote=order_value,
                            fallback_amount=estimated_bought_amount,
                            fallback_order_value_quote=order_value,
                            fallback_price=entry_price[symbol],
                        )
                        notifier.notify_buy_fill(
                            "OKX",
                            symbol,
                            f"매수 금액: {buy_summary['executed_order_value_quote']:.8f} {quote}\n"
                            f"매수 단가: {buy_summary['executed_price']:.4f}\n"
                            f"체결 수량: {buy_summary['executed_amount']:.8f} {base}",
                        )
                        trade_history.log_fill(
                            exchange_name="OKX",
                            program_name="ma_crossover_bot",
                            symbol=symbol,
                            side="buy",
                            reason="entry",
                            base_currency=base,
                            quote_currency=quote,
                            amount=estimated_bought_amount,
                            order_value_quote=order_value,
                            reference_price=last_close,
                            estimated_entry_price=entry_price[symbol],
                            entry_count_after=entry_count[symbol],
                            base_free_before=base_free,
                            quote_free_before=quote_free,
                            remaining_base_after_estimate=base_free + estimated_bought_amount,
                            timeframe=timeframe,
                            ma_period=ma_period,
                            strategy_version=strategy.version,
                            request_started_at=order_request_started_at,
                            response_received_at=order_response_received_at,
                            requested_order_value_quote=order_value,
                            raw_order=order,
                            extra={
                                "strategy_version": strategy.version,
                                "bullish_signal": bullish,
                                "signal_is_strong": signal_is_strong,
                                "gap_pct": gap_pct,
                                "take_profit_pct": take_profit_pct,
                                "stop_loss_pct": stop_loss_pct,
                                "min_volume_ratio": effective_min_volume_ratio,
                                "volume_filter_passed": volume_filter_passed,
                                "volatility_filter_passed": volatility_filter_passed,
                                "htf_bullish": htf_bullish,
                            },
                        )
                        log(
                            f"[{symbol}] 분할 매수 진행: {entry_count[symbol]}/{strategy.max_entry_count}회"
                        )
                        log(
                            f"[{symbol}] 갱신된 평균 진입가: {entry_price[symbol]:.4f}"
                        )

                # 매도 신호 발생 시, 분할 청산 + 최소 익절률 조건을 만족하면 청산
                elif exit_ready:
                    sell_ratio = strategy.sell_split_ratio
                    exit_reason_key = "take_profit"
                    sell_reason = "익절"
                    if stop_loss_triggered:
                        if partial_stop_loss_pending:
                            sell_ratio = strategy.partial_stop_loss_ratio
                            exit_reason_key = "partial_stop_loss"
                            sell_reason = "부분손절"
                        else:
                            sell_ratio = 1.0
                            exit_reason_key = "stop_loss"
                            sell_reason = "손절"
                    elif profit_protect_triggered:
                        sell_ratio = 1.0
                        exit_reason_key = "profit_protect_take_profit"
                        sell_reason = "순익보호익절"
                    elif partial_take_profit_pending:
                        sell_ratio = strategy.partial_take_profit_ratio
                        exit_reason_key = "partial_take_profit"
                        sell_reason = "부분익절"

                    sell_amount = base_free * sell_ratio
                    amount = safe_amount_to_precision(
                        exchange, symbol, sell_amount
                    )
                    full_sell_amount = safe_amount_to_precision(exchange, symbol, base_free)
                    if (
                        amount > 0
                        and min_order_amount > 0
                        and amount < min_order_amount
                        and full_sell_amount >= min_order_amount
                    ):
                        log(
                            f"[{symbol}] 부분/분할 매도 수량이 최소 주문 수량보다 작아 전량 청산으로 전환합니다."
                        )
                        amount = full_sell_amount
                        sell_ratio = 1.0
                        if exit_reason_key == "partial_take_profit":
                            exit_reason_key = "take_profit"
                            sell_reason = "익절"
                        elif exit_reason_key == "partial_stop_loss":
                            exit_reason_key = "stop_loss"
                            sell_reason = "손절"
                    if amount <= 0:
                        log(f"[{symbol}] 매도할 {base} 수량이 없습니다.")
                    elif min_order_amount > 0 and amount < min_order_amount:
                        log(
                            f"[{symbol}] 매도 수량 {amount:.8f} {base} 가 거래소 최소 주문 수량 "
                            f"{min_order_amount:.8f} {base} 보다 작아 매도를 생략합니다."
                        )
                    else:
                        structured_logger.log_strategy(
                            symbol=symbol,
                            side="exit",
                            stage="order_requested",
                            result="requested",
                            reason="market_sell_requested",
                            actual={"sell_amount": amount},
                            metrics=common_metrics,
                        )
                        log(f"[매도] 시장가 매도 시도: {symbol}, 수량={amount} {base}")
                        order_request_started_at = time.time()
                        try:
                            order = place_market_order_okx(
                                exchange,
                                symbol,
                                "sell",
                                amount,
                                tgt_ccy="base_ccy",
                            )
                        except Exception as order_error:
                            structured_logger.log_strategy(
                                symbol=symbol,
                                side="exit",
                                stage="filled",
                                result="error",
                                reason="order_failed",
                                actual={"sell_amount": amount},
                                metrics=common_metrics,
                                extra={"error": repr(order_error)},
                            )
                            structured_logger.log_system(
                                level="WARNING",
                                event="order_failed",
                                message="매도 주문 요청이 실패했습니다.",
                                symbol=symbol,
                                context={
                                    "side": "sell",
                                    "sell_amount": amount,
                                    "error": repr(order_error),
                                },
                            )
                            continue
                        order_response_received_at = time.time()
                        last_trade_at[symbol] = time.time()
                        remaining_base = max(base_free - amount, 0.0)
                        if remaining_base <= 0.0001:
                            entry_count[symbol] = 0
                        else:
                            entry_count[symbol] = max(current_entry_count - 1, 0)
                        # 손익 계산
                        entry = entry_price.get(symbol)
                        if entry:
                            realized_pnl_pct = (last_close - entry) / entry * 100
                            realized_pnl_quote = (last_close - entry) * amount
                            (
                                fee_quote_estimate,
                                net_realized_pnl_quote,
                                net_realized_pnl_pct,
                            ) = estimate_round_trip_net_pnl(
                                entry_price=entry,
                                exit_price=last_close,
                                amount=amount,
                                fee_rate_pct=config["fee_rate_pct"],
                                realized_pnl_quote=realized_pnl_quote,
                            )
                            daily_realized_pnl_quote += realized_pnl_quote
                            holding_seconds = None
                            if symbol in entry_opened_at:
                                holding_seconds = max(
                                    0.0, time.time() - entry_opened_at[symbol]
                                )
                            structured_logger.log_strategy(
                                symbol=symbol,
                                side="exit",
                                stage="filled",
                                result="filled",
                                reason=f"{exit_reason_key}_filled",
                                actual={
                                    "filled_amount": amount,
                                    "realized_pnl_pct": realized_pnl_pct,
                                    "realized_pnl_quote": realized_pnl_quote,
                                },
                                metrics={
                                    **common_metrics,
                                    "holding_seconds": holding_seconds,
                                },
                            )
                            structured_logger.log_trade_event(
                                symbol=symbol,
                                side="sell",
                                reason=exit_reason_key,
                                result="filled",
                                actual={
                                    "filled_amount": amount,
                                    "realized_pnl_pct": realized_pnl_pct,
                                    "realized_pnl_quote": realized_pnl_quote,
                                },
                                metrics={
                                    **common_metrics,
                                    "holding_seconds": holding_seconds,
                                },
                            )
                            logger.log_trade_banner(
                                BLUE,
                                f"[{symbol}] {sell_reason} 매도 주문 체결",
                                f"주문 결과: {order} | 수익률={realized_pnl_pct:.2f}%",
                            )
                            sell_summary = summarize_order_for_notification(
                                raw_order=order,
                                side="sell",
                                requested_amount=amount,
                                requested_order_value_quote=amount * last_close,
                                fallback_amount=amount,
                                fallback_order_value_quote=amount * last_close,
                                fallback_price=last_close,
                            )
                            if stop_loss_triggered:
                                notifier.notify_stop_loss_fill(
                                    "OKX",
                                    symbol,
                                    f"매도 금액: {sell_summary['executed_order_value_quote']:.4f} {quote}\n"
                                    f"매도 단가: {sell_summary['executed_price']:.4f}\n"
                                    f"체결 수량: {sell_summary['executed_amount']:.8f} {base}\n"
                                    f"수익률: {realized_pnl_pct:.2f}%\n"
                                    f"실현 손익: {realized_pnl_quote:.4f} {quote}",
                                )
                            else:
                                notifier.notify_sell_fill(
                                    "OKX",
                                    symbol,
                                    f"매도 금액: {sell_summary['executed_order_value_quote']:.4f} {quote}\n"
                                    f"매도 단가: {sell_summary['executed_price']:.4f}\n"
                                    f"체결 수량: {sell_summary['executed_amount']:.8f} {base}\n"
                                    f"수익률: {realized_pnl_pct:.2f}%\n"
                                    f"실현 손익: {realized_pnl_quote:.4f} {quote}",
                                )
                            log(
                                f"[{symbol}] 실현 손익: {realized_pnl_quote:.4f} {quote} | "
                                f"오늘 누적 실현 손익: {daily_realized_pnl_quote:.4f} {quote}"
                            )
                            trade_history.log_fill(
                                exchange_name="OKX",
                                program_name="ma_crossover_bot",
                                symbol=symbol,
                                side="sell",
                                reason=exit_reason_key,
                                base_currency=base,
                                quote_currency=quote,
                                amount=amount,
                                order_value_quote=amount * last_close,
                                reference_price=last_close,
                                estimated_entry_price=entry,
                                realized_pnl_pct=realized_pnl_pct,
                                realized_pnl_quote=realized_pnl_quote,
                                daily_realized_pnl_quote_after=daily_realized_pnl_quote,
                                entry_count_after=entry_count.get(symbol, 0),
                                base_free_before=base_free,
                                quote_free_before=quote_free,
                                remaining_base_after_estimate=remaining_base,
                                timeframe=timeframe,
                                ma_period=ma_period,
                                strategy_version=strategy.version,
                                fee_rate_pct=config["fee_rate_pct"],
                                fee_quote_estimate=fee_quote_estimate,
                                net_realized_pnl_quote=net_realized_pnl_quote,
                                net_realized_pnl_pct=net_realized_pnl_pct,
                                highest_price_since_entry=highest_price_since_entry.get(symbol),
                                lowest_price_since_entry=lowest_price_since_entry.get(symbol),
                                mfe_pct=mfe_pct,
                                mae_pct=mae_pct,
                                request_started_at=order_request_started_at,
                                response_received_at=order_response_received_at,
                                requested_amount=amount,
                                raw_order=order,
                                extra={
                                    "strategy_version": strategy.version,
                                    "sell_ratio": sell_ratio,
                                    "bearish_signal": bearish,
                                    "signal_is_strong": signal_is_strong,
                                    "gap_pct": gap_pct,
                                    "take_profit_pct": take_profit_pct,
                                    "stop_loss_pct": stop_loss_pct,
                                    "current_net_pnl_pct_estimate": current_net_realized_pnl_pct,
                                    "fee_protect_min_net_pnl_pct": strategy.fee_protect_min_net_pnl_pct,
                                    "profit_protect_triggered": profit_protect_triggered,
                                    "pnl_pct_at_decision": pnl_pct,
                                    "htf_bearish": htf_bearish,
                                    "holding_seconds": holding_seconds,
                                },
                            )
                            if exit_reason_key == "partial_take_profit" and remaining_base > 0.0001:
                                partial_take_profit_done[symbol] = True
                                partial_take_profit_last_at[symbol] = time.time()
                            if exit_reason_key == "partial_stop_loss" and remaining_base > 0.0001:
                                partial_stop_loss_done[symbol] = True
                            # 포지션 청산 후 진입가 제거
                            if remaining_base <= 0.0001:
                                entry_price.pop(symbol, None)
                                entry_opened_at.pop(symbol, None)
                                highest_price_since_entry.pop(symbol, None)
                                lowest_price_since_entry.pop(symbol, None)
                                partial_take_profit_done.pop(symbol, None)
                                partial_stop_loss_done.pop(symbol, None)
                        else:
                            structured_logger.log_strategy(
                                symbol=symbol,
                                side="exit",
                                stage="filled",
                                result="filled",
                                reason="sell_filled_entry_unknown",
                                actual={"filled_amount": amount},
                                metrics=common_metrics,
                            )
                            structured_logger.log_trade_event(
                                symbol=symbol,
                                side="sell",
                                reason="unknown_entry_sell",
                                result="filled",
                                actual={"filled_amount": amount},
                                metrics=common_metrics,
                            )
                            logger.log_trade_banner(
                                BLUE,
                                f"[{symbol}] {sell_reason} 매도 주문 체결",
                                f"주문 결과: {order}",
                            )
                            trade_history.log_fill(
                                exchange_name="OKX",
                                program_name="ma_crossover_bot",
                                symbol=symbol,
                                side="sell",
                                reason=exit_reason_key,
                                base_currency=base,
                                quote_currency=quote,
                                amount=amount,
                                order_value_quote=amount * last_close,
                                reference_price=last_close,
                                daily_realized_pnl_quote_after=daily_realized_pnl_quote,
                                entry_count_after=entry_count.get(symbol, 0),
                                base_free_before=base_free,
                                quote_free_before=quote_free,
                                remaining_base_after_estimate=remaining_base,
                                timeframe=timeframe,
                                ma_period=ma_period,
                                strategy_version=strategy.version,
                                highest_price_since_entry=highest_price_since_entry.get(symbol),
                                lowest_price_since_entry=lowest_price_since_entry.get(symbol),
                                mfe_pct=mfe_pct,
                                mae_pct=mae_pct,
                                request_started_at=order_request_started_at,
                                response_received_at=order_response_received_at,
                                requested_amount=amount,
                                raw_order=order,
                                extra={
                                    "strategy_version": strategy.version,
                                    "sell_ratio": sell_ratio,
                                    "bearish_signal": bearish,
                                    "signal_is_strong": signal_is_strong,
                                    "gap_pct": gap_pct,
                                    "current_net_pnl_pct_estimate": current_net_realized_pnl_pct,
                                    "fee_protect_min_net_pnl_pct": strategy.fee_protect_min_net_pnl_pct,
                                    "profit_protect_triggered": profit_protect_triggered,
                                    "entry_price_unknown": True,
                                    "htf_bearish": htf_bearish,
                                },
                            )
                            if remaining_base <= 0.0001:
                                entry_opened_at.pop(symbol, None)
                                partial_take_profit_done.pop(symbol, None)
                                partial_stop_loss_done.pop(symbol, None)
                        log(
                            f"[{symbol}] 분할 매도 후 남은 진입 카운트: {entry_count.get(symbol, 0)}"
                        )
                else:
                    log(f"[{symbol}] 주문 조건에 해당하지 않아 대기합니다.")

            except Exception as e:
                log(f"[{symbol}] 에러 발생: {repr(e)}")
                log(traceback.format_exc().rstrip())
                structured_logger.log_system(
                    level="ERROR",
                    event="loop_error",
                    message="심볼 처리 중 예외가 발생했습니다.",
                    symbol=symbol,
                    context={"error": repr(e)},
                )
                notifier.notify_error_message("OKX", symbol, repr(e))

        # 사용자 설정에 따라 반복
        time.sleep(strategy.loop_interval_sec)


if __name__ == "__main__":
    run_bot()
