"""장기(매크로) 추세 게이트.

상위 타임프레임(5m) 종가의 장기 EMA(기본 40봉=200분) 위에 있을 때만 신규 롱 진입을
허용하는 게이트. 7일 백테스트에서 강신호 알트 진입 모집단의 EV 를 증분 +7.55%p
개선했다(아래 macro EMA 미달 진입이 손실군). 데이터/가격이 부족하면 차단하지 않는다(fail-open).
"""

from __future__ import annotations

from core.strategy.indicators import calc_ema_series


def compute_macro_trend_gate(
    htf_closes: list[float] | None,
    *,
    period: int,
    enabled: bool,
) -> tuple[bool, float | None]:
    """(통과여부, macro_ema) 를 반환한다.

    - enabled=False 이거나 데이터가 부족하면 (True, None) 으로 통과시킨다(fail-open).
    - 그 외에는 마지막 종가 > 장기 EMA 일 때만 통과.
    """
    if not enabled or period <= 0:
        return True, None
    if not htf_closes or len(htf_closes) < period:
        return True, None
    macro_ema = calc_ema_series(htf_closes, period)[-1]
    return htf_closes[-1] > macro_ema, macro_ema
