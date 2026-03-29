"""
작업 요약
- 복구 불가 포지션을 현재가로 bootstrap 하지 않고 보류하는 가드를 공통화했다.
- 포지션 상태 복구 실패 시 경고 로그를 한 곳에서 남기도록 정리했다.
"""

from __future__ import annotations


def handle_unrecoverable_position(
    *,
    warned_symbols: set[str],
    symbol: str,
    has_position: bool,
    average_entry_price: float | None,
    log,
    structured_logger,
    context: dict,
    message: str,
) -> bool:
    if has_position and average_entry_price is None:
        if symbol not in warned_symbols:
            log(
                f"[{symbol}] 복구 가능한 진입가 없이 보유 포지션만 감지되었습니다. "
                "현재가로 임시 진입가를 만들지 않고 자동 매매를 보류합니다."
            )
            structured_logger.log_system(
                level="WARNING",
                event="position_state_unrecoverable",
                message=message,
                symbol=symbol,
                context=context,
            )
            warned_symbols.add(symbol)
        return True

    if not has_position:
        warned_symbols.discard(symbol)
    return False
