from __future__ import annotations


def log_order_failure(
    *,
    structured_logger,
    symbol: str,
    side: str,
    message: str,
    actual: dict,
    metrics: dict,
    error: Exception,
    extra: dict | None = None,
) -> None:
    payload_extra = {"error": repr(error)}
    if extra:
        payload_extra.update(extra)
    structured_logger.log_strategy(
        symbol=symbol,
        side=side,
        stage="filled",
        result="error",
        reason="order_failed",
        actual=actual,
        metrics=metrics,
        extra=payload_extra,
    )
    structured_logger.log_system(
        level="WARNING",
        event="order_failed",
        message=message,
        symbol=symbol,
        context={
            "side": side,
            **actual,
            "error": repr(error),
        },
    )

