"""
작업 요약
- mean_reversion 하단 근접 probe 후보는 raw signal 단계에서 reclaim 과 구분해 기록
- no_entry_signal 포괄 차단을 raw 신호, squeeze, mean_reversion 컨텍스트, 최종 integrity 단계로 세분화
- 거래량 상한 초과 신호를 소액/추가확인 후보로 낮춘 경우 volume_cap 단계를 통과하도록 확장
- OKX funding rate 과열 차단 단계를 알트/BTC 진입 퍼널에 추가
- 2026-04-10: 알트 보수형 튜닝용 최대 이격도와 최대 거래량 상한 단계를 퍼널에 추가했다.
- 2026-04-09: 손절 후 패턴 기반 재진입 차단 단계를 퍼널에 추가해 reason 코드로 추적할 수 있게 확장
- 알트/BTC 진입, 추가매수, 청산 퍼널 step 생성기를 공통 모듈로 분리했다.
- reason 코드와 단계 구성을 한 곳에서 유지하도록 정리했다.
- RSI, MACD, 신호 스코어, 볼린저 밴드 폭 같은 보조 필터 단계를 퍼널에 반영했다.
"""

from __future__ import annotations

from structured_log_manager import FunnelStep


def build_alt_entry_steps(
    *,
    entry_signal: bool,
    bullish: bool,
    trend_follow_entry: bool,
    signal_is_strong: bool,
    signal_score: float,
    min_signal_score: float,
    gap_pct: float,
    min_gap_pct: float,
    max_gap_pct: float,
    gap_within_upper_bound: bool,
    rsi_filter_passed: bool,
    macd_filter_passed: bool,
    htf_bullish: bool,
    volume_filter_passed: bool,
    volume_ratio: float | None,
    effective_min_volume_ratio: float,
    max_volume_ratio: float,
    volume_within_upper_bound: bool,
    volume_cap_downgrade_allowed: bool,
    volume_cap_downgrade_reason: str | None,
    volume_cap_hard_max_ratio: float | None,
    volatility_filter_passed: bool,
    avg_abs_change_pct: float | None,
    min_volatility_pct: float,
    max_volatility_pct: float,
    in_cooldown: bool,
    seconds_since_last_trade: float,
    can_average_down: bool,
    last_close: float,
    avg_entry_price: float | None,
    current_entry_count: int,
    max_entry_count: int,
    daily_loss_limit_reached: bool,
    daily_realized_pnl_quote: float,
    max_daily_loss_quote: float,
    order_value_quote: float,
    min_buy_order_value: float,
    entry_strategy_key: str = "ma",
    order_value_block_reason: str = "order_value_too_small",
    squeeze_band_passed: bool = True,
    squeeze_volume_passed: bool = True,
    squeeze_breakout_passed: bool = True,
    mean_reversion_lower_reclaim_confirmed: bool = False,
    mean_reversion_lower_near_probe_allowed: bool = False,
    mean_reversion_bb_lower_distance_pct: float | None = None,
    mean_reversion_lower_near_max_distance_pct: float | None = None,
    atr_context_passed: bool = True,
    range_context_passed: bool = True,
    falling_knife_blocked: bool = False,
    funding_rate_filter_passed: bool = True,
    funding_rate: float | None = None,
    max_funding_rate: float | None = None,
    stop_loss_pattern_blocked: bool = False,
    stop_loss_pattern_elapsed_sec: float | None = None,
    stop_loss_pattern_min_cooldown_sec: int | None = None,
    stop_loss_pattern_signal_score: float | None = None,
    stop_loss_pattern_min_signal_score: float | None = None,
    stop_loss_pattern_volume_ratio: float | None = None,
    stop_loss_pattern_required_volume_ratio: float | None = None,
):
    normalized_strategy = str(entry_strategy_key or "ma").strip().lower()
    raw_signal_passed = bullish or trend_follow_entry
    raw_signal_reason = "trend_signal_missing"
    raw_signal_required = {"bullish_or_trend_follow_entry": True}
    if normalized_strategy in {"mean_reversion", "low_energy_probe"}:
        raw_signal_passed = bullish
        raw_signal_reason = "mean_reversion_lower_reclaim_missing"
        raw_signal_required = {
            "bollinger_lower_reclaim_or_lower_near_probe": True,
            "lower_near_max_distance_pct": mean_reversion_lower_near_max_distance_pct,
        }
    elif normalized_strategy == "squeeze":
        raw_signal_passed = squeeze_band_passed and squeeze_volume_passed and squeeze_breakout_passed
        raw_signal_reason = "squeeze_entry_signal_missing"
        raw_signal_required = {
            "squeeze_band_passed": True,
            "squeeze_volume_passed": True,
            "squeeze_breakout_passed": True,
        }

    steps = [
        FunnelStep(
            stage="raw_entry_signal",
            passed=raw_signal_passed,
            reason=raw_signal_reason,
            actual={
                "strategy_key": normalized_strategy,
                "bullish_signal": bullish,
                "trend_follow_entry": trend_follow_entry,
                "squeeze_band_passed": squeeze_band_passed,
                "squeeze_volume_passed": squeeze_volume_passed,
                "squeeze_breakout_passed": squeeze_breakout_passed,
                "lower_reclaim_confirmed": mean_reversion_lower_reclaim_confirmed,
                "lower_near_probe_allowed": mean_reversion_lower_near_probe_allowed,
                "bb_lower_distance_pct": mean_reversion_bb_lower_distance_pct,
            },
            required=raw_signal_required,
        ),
        FunnelStep(
            stage="squeeze_band",
            passed=(normalized_strategy != "squeeze" or squeeze_band_passed),
            reason="squeeze_band_not_tight",
            actual={"squeeze_band_passed": squeeze_band_passed},
            required={"squeeze_band_passed": True},
        ),
        FunnelStep(
            stage="squeeze_volume",
            passed=(normalized_strategy != "squeeze" or squeeze_volume_passed),
            reason="squeeze_volume_not_expanded",
            actual={"squeeze_volume_passed": squeeze_volume_passed},
            required={"squeeze_volume_passed": True},
        ),
        FunnelStep(
            stage="squeeze_breakout",
            passed=(normalized_strategy != "squeeze" or squeeze_breakout_passed),
            reason="squeeze_breakout_missing",
            actual={"squeeze_breakout_passed": squeeze_breakout_passed},
            required={"squeeze_breakout_passed": True},
        ),
        FunnelStep(
            stage="distance",
            passed=signal_is_strong,
            reason="signal_score_low",
            actual={"gap_pct": gap_pct, "signal_score": signal_score},
            required={"min_gap_pct": min_gap_pct, "min_signal_score": min_signal_score},
        ),
        FunnelStep(
            stage="distance_cap",
            passed=gap_within_upper_bound,
            reason="gap_too_large",
            actual={"gap_pct": gap_pct},
            required={"max_gap_pct": max_gap_pct},
        ),
        FunnelStep(
            stage="rsi",
            passed=rsi_filter_passed,
            reason="rsi_filter_blocked",
            actual={"rsi_filter_passed": rsi_filter_passed},
            required={"rsi_filter_passed": True},
        ),
        FunnelStep(
            stage="macd",
            passed=macd_filter_passed,
            reason="macd_filter_blocked",
            actual={"macd_filter_passed": macd_filter_passed},
            required={"macd_histogram_positive": True},
        ),
        FunnelStep(
            stage="mean_reversion_atr_context",
            passed=(normalized_strategy not in {"mean_reversion", "low_energy_probe"} or atr_context_passed),
            reason="mean_reversion_atr_context_blocked",
            actual={"atr_context_passed": atr_context_passed},
            required={"atr_context_passed": True},
        ),
        FunnelStep(
            stage="mean_reversion_range_context",
            passed=(normalized_strategy not in {"mean_reversion", "low_energy_probe"} or range_context_passed),
            reason="mean_reversion_range_context_blocked",
            actual={"range_context_passed": range_context_passed},
            required={"range_context_passed": True},
        ),
        FunnelStep(
            stage="mean_reversion_falling_knife",
            passed=(normalized_strategy not in {"mean_reversion", "low_energy_probe"} or not falling_knife_blocked),
            reason="mean_reversion_falling_knife_blocked",
            actual={"falling_knife_blocked": falling_knife_blocked},
            required={"falling_knife_blocked": False},
        ),
        FunnelStep(
            stage="entry_signal_integrity",
            passed=entry_signal,
            reason="entry_signal_unclassified_block",
            actual={"entry_signal": entry_signal, "strategy_key": normalized_strategy},
            required={"entry_signal": True},
        ),
        FunnelStep(
            stage="higher_timeframe",
            passed=htf_bullish,
            reason="higher_timeframe_not_bullish",
            actual={"htf_bullish": htf_bullish},
            required={"htf_bullish": True},
        ),
        FunnelStep(
            stage="volume",
            passed=volume_filter_passed,
            reason="volume_low",
            actual={"volume_ratio": volume_ratio},
            required={"min_volume_ratio": effective_min_volume_ratio},
        ),
        FunnelStep(
            stage="volume_cap",
            passed=(volume_within_upper_bound or volume_cap_downgrade_allowed),
            reason="volume_spike_too_high",
            actual={
                "volume_ratio": volume_ratio,
                "downgrade_allowed": volume_cap_downgrade_allowed,
                "downgrade_reason": volume_cap_downgrade_reason,
            },
            required={
                "max_volume_ratio": max_volume_ratio,
                "hard_max_volume_ratio": volume_cap_hard_max_ratio,
            },
        ),
        FunnelStep(
            stage="funding_rate",
            passed=funding_rate_filter_passed,
            reason="funding_rate_overheated",
            actual={"funding_rate": funding_rate},
            required={"max_funding_rate": max_funding_rate},
        ),
        FunnelStep(
            stage="volatility",
            passed=volatility_filter_passed,
            reason="volatility_out_of_range",
            actual={"avg_abs_change_pct": avg_abs_change_pct},
            required={
                "min_volatility_pct": min_volatility_pct,
                "max_volatility_pct": max_volatility_pct,
            },
        ),
        FunnelStep(
            stage="cooldown",
            passed=not in_cooldown,
            reason="cooldown_active",
            actual={"seconds_since_last_trade": seconds_since_last_trade},
            required={"cooldown_inactive": True},
        ),
        FunnelStep(
            stage="stop_loss_reentry",
            passed=not stop_loss_pattern_blocked,
            reason="stop_loss_pattern_reentry_blocked",
            actual={
                "elapsed_since_stop_loss_sec": stop_loss_pattern_elapsed_sec,
                "signal_score": stop_loss_pattern_signal_score,
                "volume_ratio": stop_loss_pattern_volume_ratio,
            },
            required={
                "min_cooldown_sec": stop_loss_pattern_min_cooldown_sec,
                "min_signal_score": stop_loss_pattern_min_signal_score,
                "min_volume_ratio": stop_loss_pattern_required_volume_ratio,
            },
        ),
        FunnelStep(
            stage="position_rule",
            passed=can_average_down,
            reason="avg_price_rule_block",
            actual={"last_close": last_close, "avg_entry_price": avg_entry_price},
            required={"required_price_lte": avg_entry_price},
        ),
        FunnelStep(
            stage="entry_limit",
            passed=current_entry_count < max_entry_count,
            reason="max_entry_reached",
            actual={"entry_count": current_entry_count},
            required={"max_entry_count": max_entry_count},
        ),
        FunnelStep(
            stage="risk_limit",
            passed=not daily_loss_limit_reached,
            reason="daily_loss_limit_reached",
            actual={"daily_realized_pnl_quote": daily_realized_pnl_quote},
            required={"min_daily_realized_pnl_quote": -max_daily_loss_quote},
        ),
        FunnelStep(
            stage="order_value",
            passed=order_value_quote > min_buy_order_value,
            reason=order_value_block_reason,
            actual={"order_value_quote": order_value_quote},
            required={"min_buy_order_value": min_buy_order_value},
        ),
    ]
    return steps


def build_alt_exit_steps(
    *,
    has_position: bool,
    stop_loss_triggered: bool,
    profit_protect_triggered: bool,
    break_even_guard_triggered: bool,
    volume_spike_exit_triggered: bool,
    bearish: bool,
    in_cooldown: bool,
    seconds_since_last_trade: float,
    signal_is_strong: bool,
    gap_pct: float,
    min_gap_pct: float,
    htf_bearish: bool,
    take_profit_ready: bool,
    pnl_pct: float | None,
    current_net_realized_pnl_pct: float | None,
    mfe_pct: float | None,
    min_take_profit_pct: float,
    fee_protect_min_net_pnl_pct: float,
    break_even_guard_min_mfe_pct: float,
    break_even_guard_floor_net_pnl_pct: float,
):
    return [
        FunnelStep(
            stage="position",
            passed=has_position,
            reason="no_position",
            actual={"has_position": has_position},
            required={"has_position": True},
        ),
        FunnelStep(
            stage="exit_trigger",
            passed=(stop_loss_triggered or profit_protect_triggered or break_even_guard_triggered or volume_spike_exit_triggered or bearish),
            reason="no_exit_signal",
            actual={
                "stop_loss_triggered": stop_loss_triggered,
                "profit_protect_triggered": profit_protect_triggered,
                "break_even_guard_triggered": break_even_guard_triggered,
                "volume_spike_exit_triggered": volume_spike_exit_triggered,
                "bearish_signal": bearish,
            },
            required={"exit_signal": True},
        ),
        FunnelStep(
            stage="cooldown",
            passed=(stop_loss_triggered or profit_protect_triggered or break_even_guard_triggered or volume_spike_exit_triggered or not in_cooldown),
            reason="cooldown_active",
            actual={"seconds_since_last_trade": seconds_since_last_trade},
            required={"cooldown_inactive": True},
        ),
        FunnelStep(
            stage="distance",
            passed=(stop_loss_triggered or profit_protect_triggered or break_even_guard_triggered or volume_spike_exit_triggered or signal_is_strong),
            reason="distance_too_small",
            actual={"gap_pct": gap_pct},
            required={"min_gap_pct": min_gap_pct},
        ),
        FunnelStep(
            stage="higher_timeframe",
            passed=(stop_loss_triggered or profit_protect_triggered or break_even_guard_triggered or volume_spike_exit_triggered or htf_bearish),
            reason="higher_timeframe_not_bearish",
            actual={"htf_bearish": htf_bearish},
            required={"htf_bearish": True},
        ),
        FunnelStep(
            stage="take_profit",
            passed=(stop_loss_triggered or profit_protect_triggered or break_even_guard_triggered or volume_spike_exit_triggered or take_profit_ready),
            reason="take_profit_not_reached",
            actual={
                "pnl_pct": pnl_pct,
                "net_pnl_pct_estimate": current_net_realized_pnl_pct,
                "mfe_pct": mfe_pct,
            },
            required={
                "min_take_profit_pct": min_take_profit_pct,
                "fee_protect_min_net_pnl_pct": fee_protect_min_net_pnl_pct,
                "break_even_guard_min_mfe_pct": break_even_guard_min_mfe_pct,
                "break_even_guard_floor_net_pnl_pct": break_even_guard_floor_net_pnl_pct,
            },
        ),
    ]


def build_btc_entry_steps(
    *,
    entry_signal: bool,
    bullish: bool,
    trend_follow_entry: bool,
    ema_aligned: bool,
    price_above_fast: bool,
    ema_slope_positive: bool,
    ema_spread_pct: float,
    effective_min_ema_spread_pct: float,
    signal_score: float,
    min_signal_score: float,
    rsi_filter_passed: bool,
    bb_width_filter_passed: bool,
    bb_width_pct: float | None,
    min_bb_width_pct: float,
    max_bb_width_pct: float,
    has_position: bool,
    in_cooldown: bool,
    cooldown_remaining: float,
    base_cooldown_remaining: float,
    stop_loss_cooldown_remaining: float,
    profit_exit_cooldown_remaining: float,
    low_energy_guard_active: bool,
    low_energy_avg_volume_ratio: float,
    low_energy_avg_abs_change_pct: float,
    low_energy_ready_count: int,
    symbol_regime_blocks_entry: bool,
    symbol_regime: str,
    symbol_regime_requires_fresh_cross: bool,
    volume_filter_passed: bool,
    volume_ratio: float | None,
    effective_min_volume_ratio: float,
    atr_filter_passed: bool,
    atr_pct: float,
    effective_min_atr_pct: float,
    max_atr_pct: float,
    confirm_bullish: bool,
    daily_loss_limit_reached: bool,
    daily_realized_pnl_quote: float,
    max_daily_loss_quote: float,
    remaining_budget_quote: float,
    current_cost_basis_quote: float,
    target_budget_quote: float,
    order_value: float,
    min_buy_order_value: float,
    estimated_entry_amount: float,
    min_order_amount: float,
    entry_strategy_key: str = "ema",
    low_energy_probe_allowed: bool = False,
    low_energy_probe_reason: str | None = None,
    low_energy_probe_min_signal_score: float | None = None,
    low_energy_probe_min_volume_ratio: float | None = None,
    low_energy_probe_max_atr_percentile: float | None = None,
    funding_rate_filter_passed: bool = True,
    funding_rate: float | None = None,
    max_funding_rate: float | None = None,
    stop_loss_pattern_blocked: bool = False,
    stop_loss_pattern_elapsed_sec: float | None = None,
    stop_loss_pattern_min_cooldown_sec: int | None = None,
    stop_loss_pattern_signal_score: float | None = None,
    stop_loss_pattern_min_signal_score: float | None = None,
):
    normalized_strategy = str(entry_strategy_key or "ema").strip().lower()
    raw_signal_passed = bullish or trend_follow_entry
    raw_signal_reason = "trend_signal_missing"
    raw_signal_required = {"bullish_signal_or_trend_follow_entry": True}
    if normalized_strategy == "donchian":
        raw_signal_passed = bullish
        raw_signal_reason = "donchian_breakout_missing"
        raw_signal_required = {"donchian_breakout": True}

    return [
        FunnelStep(
            stage="raw_entry_signal",
            passed=raw_signal_passed,
            reason=raw_signal_reason,
            actual={
                "strategy_key": normalized_strategy,
                "bullish_signal": bullish,
                "trend_follow_entry": trend_follow_entry,
                "ema_aligned": ema_aligned,
                "price_above_fast": price_above_fast,
                "ema_slope_positive": ema_slope_positive,
                "ema_spread_pct": ema_spread_pct,
                "signal_score": signal_score,
            },
            required={
                "min_ema_spread_pct": effective_min_ema_spread_pct,
                "min_signal_score": min_signal_score,
                **raw_signal_required,
            },
        ),
        FunnelStep(
            stage="rsi",
            passed=rsi_filter_passed,
            reason="rsi_filter_blocked",
            actual={"rsi_filter_passed": rsi_filter_passed},
            required={"rsi_filter_passed": True},
        ),
        FunnelStep(
            stage="bb_width",
            passed=bb_width_filter_passed,
            reason="bb_width_out_of_range",
            actual={"bb_width_pct": bb_width_pct},
            required={
                "min_bb_width_pct": min_bb_width_pct,
                "max_bb_width_pct": max_bb_width_pct,
            },
        ),
        FunnelStep(
            stage="entry_signal_integrity",
            passed=entry_signal,
            reason="entry_signal_unclassified_block",
            actual={"entry_signal": entry_signal, "strategy_key": normalized_strategy},
            required={"entry_signal": True},
        ),
        FunnelStep(
            stage="position",
            passed=not has_position,
            reason="position_exists",
            actual={"has_position": has_position},
            required={"has_position": False},
        ),
        FunnelStep(
            stage="cooldown",
            passed=not in_cooldown,
            reason="cooldown_active",
            actual={
                "cooldown_remaining_sec": cooldown_remaining,
                "base_cooldown_remaining_sec": base_cooldown_remaining,
                "stop_loss_cooldown_remaining_sec": stop_loss_cooldown_remaining,
                "profit_exit_cooldown_remaining_sec": profit_exit_cooldown_remaining,
            },
            required={"cooldown_inactive": True},
        ),
        FunnelStep(
            stage="stop_loss_reentry",
            passed=not stop_loss_pattern_blocked,
            reason="stop_loss_pattern_reentry_blocked",
            actual={
                "elapsed_since_stop_loss_sec": stop_loss_pattern_elapsed_sec,
                "signal_score": stop_loss_pattern_signal_score,
            },
            required={
                "min_cooldown_sec": stop_loss_pattern_min_cooldown_sec,
                "min_signal_score": stop_loss_pattern_min_signal_score,
            },
        ),
        FunnelStep(
            stage="market_regime",
            passed=not low_energy_guard_active,
            reason=low_energy_probe_reason or "low_energy_market",
            actual={
                "probe_allowed": low_energy_probe_allowed,
                "avg_volume_ratio": low_energy_avg_volume_ratio,
                "avg_abs_change_pct": low_energy_avg_abs_change_pct,
                "ready_count": low_energy_ready_count,
                "signal_score": signal_score,
                "volume_ratio": volume_ratio,
                "atr_pct": atr_pct,
            },
            required={
                "low_energy_market_inactive_or_probe_allowed": True,
                "probe_min_signal_score": low_energy_probe_min_signal_score,
                "probe_min_volume_ratio": low_energy_probe_min_volume_ratio,
                "probe_max_atr_percentile": low_energy_probe_max_atr_percentile,
            },
        ),
        FunnelStep(
            stage="symbol_regime",
            passed=not symbol_regime_blocks_entry,
            reason="symbol_regime_blocks_entry",
            actual={"symbol_regime": symbol_regime},
            required={"symbol_regime_allows_entry": True},
        ),
        FunnelStep(
            stage="regime_entry_signal",
            passed=(not symbol_regime_requires_fresh_cross or bullish),
            reason="regime_requires_fresh_cross",
            actual={
                "symbol_regime": symbol_regime,
                "bullish_signal": bullish,
            },
            required={"fresh_bullish_cross_required": True},
        ),
        FunnelStep(
            stage="volume",
            passed=volume_filter_passed,
            reason="volume_low" if volume_ratio is not None else "volume_data_missing",
            actual={"volume_ratio": volume_ratio},
            required={"min_volume_ratio": effective_min_volume_ratio},
        ),
        FunnelStep(
            stage="funding_rate",
            passed=funding_rate_filter_passed,
            reason="funding_rate_overheated",
            actual={"funding_rate": funding_rate},
            required={"max_funding_rate": max_funding_rate},
        ),
        FunnelStep(
            stage="atr",
            passed=atr_filter_passed,
            reason="atr_out_of_range",
            actual={"atr_pct": atr_pct},
            required={
                "min_atr_pct": effective_min_atr_pct,
                "max_atr_pct": max_atr_pct,
            },
        ),
        FunnelStep(
            stage="higher_timeframe",
            passed=confirm_bullish,
            reason="higher_timeframe_not_bullish",
            actual={"confirm_bullish": confirm_bullish},
            required={"confirm_bullish": True},
        ),
        FunnelStep(
            stage="risk_limit",
            passed=not daily_loss_limit_reached,
            reason="daily_loss_limit_reached",
            actual={"daily_realized_pnl_quote": daily_realized_pnl_quote},
            required={"min_daily_realized_pnl_quote": -max_daily_loss_quote},
        ),
        FunnelStep(
            stage="portfolio_budget",
            passed=remaining_budget_quote > 0,
            reason="portfolio_budget_exhausted",
            actual={
                "current_cost_basis_quote": current_cost_basis_quote,
                "remaining_budget_quote": remaining_budget_quote,
            },
            required={"portfolio_target_budget_quote": target_budget_quote},
        ),
        FunnelStep(
            stage="order_value",
            passed=order_value > min_buy_order_value,
            reason="order_value_too_small",
            actual={"order_value_quote": order_value},
            required={"min_buy_order_value": min_buy_order_value},
        ),
        FunnelStep(
            stage="order_amount",
            passed=estimated_entry_amount >= min_order_amount,
            reason="order_amount_too_small",
            actual={"order_amount": estimated_entry_amount},
            required={"min_order_amount": min_order_amount},
        ),
    ]


def build_btc_add_on_steps(
    *,
    has_position: bool,
    add_on_profit_ready: bool,
    pnl_pct: float | None,
    min_pnl_pct: float,
    add_on_limit_available: bool,
    add_on_count: int,
    max_add_ons: int,
    trailing_armed: bool,
    entry_signal: bool,
    bullish: bool,
    trend_follow_entry: bool,
    in_cooldown: bool,
    cooldown_remaining: float,
    profit_exit_cooldown_remaining: float,
    volume_filter_passed: bool,
    volume_ratio: float | None,
    effective_min_volume_ratio: float,
    atr_filter_passed: bool,
    atr_pct: float,
    min_atr_pct: float,
    max_atr_pct: float,
    confirm_bullish: bool,
    daily_loss_limit_reached: bool,
    daily_realized_pnl_quote: float,
    max_daily_loss_quote: float,
    remaining_budget_quote: float,
    current_cost_basis_quote: float,
    target_budget_quote: float,
    add_on_order_value: float,
    min_buy_order_value: float,
    estimated_add_on_amount: float,
    min_order_amount: float,
):
    return [
        FunnelStep(
            stage="add_on_position",
            passed=has_position,
            reason="no_position",
            actual={"has_position": has_position},
            required={"has_position": True},
        ),
        FunnelStep(
            stage="add_on_profit",
            passed=add_on_profit_ready,
            reason="pyramid_profit_not_reached",
            actual={"pnl_pct": pnl_pct},
            required={"min_pnl_pct": min_pnl_pct},
        ),
        FunnelStep(
            stage="add_on_limit",
            passed=add_on_limit_available,
            reason="pyramid_limit_reached",
            actual={"add_on_count": add_on_count},
            required={"max_add_ons": max_add_ons},
        ),
        FunnelStep(
            stage="add_on_trailing",
            passed=not trailing_armed,
            reason="trailing_already_armed",
            actual={"trailing_armed": trailing_armed},
            required={"trailing_armed": False},
        ),
        FunnelStep(
            stage="add_on_trend",
            passed=entry_signal,
            reason="add_on_entry_signal_missing",
            actual={
                "bullish_signal": bullish,
                "trend_follow_entry": trend_follow_entry,
            },
            required={"bullish_signal_or_trend_follow_entry": True},
        ),
        FunnelStep(
            stage="add_on_cooldown",
            passed=not in_cooldown,
            reason="cooldown_active",
            actual={
                "cooldown_remaining_sec": cooldown_remaining,
                "profit_exit_cooldown_remaining_sec": profit_exit_cooldown_remaining,
            },
            required={"cooldown_inactive": True},
        ),
        FunnelStep(
            stage="add_on_volume",
            passed=volume_filter_passed,
            reason="volume_low" if volume_ratio is not None else "volume_data_missing",
            actual={"volume_ratio": volume_ratio},
            required={"min_volume_ratio": effective_min_volume_ratio},
        ),
        FunnelStep(
            stage="add_on_atr",
            passed=atr_filter_passed,
            reason="atr_out_of_range",
            actual={"atr_pct": atr_pct},
            required={"min_atr_pct": min_atr_pct, "max_atr_pct": max_atr_pct},
        ),
        FunnelStep(
            stage="add_on_higher_timeframe",
            passed=confirm_bullish,
            reason="higher_timeframe_not_bullish",
            actual={"confirm_bullish": confirm_bullish},
            required={"confirm_bullish": True},
        ),
        FunnelStep(
            stage="add_on_risk_limit",
            passed=not daily_loss_limit_reached,
            reason="daily_loss_limit_reached",
            actual={"daily_realized_pnl_quote": daily_realized_pnl_quote},
            required={"min_daily_realized_pnl_quote": -max_daily_loss_quote},
        ),
        FunnelStep(
            stage="add_on_portfolio_budget",
            passed=remaining_budget_quote > 0,
            reason="portfolio_budget_exhausted",
            actual={
                "current_cost_basis_quote": current_cost_basis_quote,
                "remaining_budget_quote": remaining_budget_quote,
            },
            required={"portfolio_target_budget_quote": target_budget_quote},
        ),
        FunnelStep(
            stage="add_on_order_value",
            passed=add_on_order_value > min_buy_order_value,
            reason="order_value_too_small",
            actual={"order_value_quote": add_on_order_value},
            required={"min_buy_order_value": min_buy_order_value},
        ),
        FunnelStep(
            stage="add_on_order_amount",
            passed=estimated_add_on_amount >= min_order_amount,
            reason="order_amount_too_small",
            actual={"order_amount": estimated_add_on_amount},
            required={"min_order_amount": min_order_amount},
        ),
    ]


def build_btc_exit_steps(
    *,
    has_position: bool,
    stop_triggered: bool,
    partial_take_profit_triggered: bool,
    profit_protect_triggered: bool,
    trailing_stop_triggered: bool,
    donchian_failure_triggered: bool,
    trend_exit_triggered: bool,
    estimated_exit_amount: float,
    min_order_amount: float,
    sell_order_value_quote: float,
    min_sell_order_value: float,
):
    return [
        FunnelStep(
            stage="position",
            passed=has_position,
            reason="no_position",
            actual={"has_position": has_position},
            required={"has_position": True},
        ),
        FunnelStep(
            stage="exit_trigger",
            passed=(
                stop_triggered
                or partial_take_profit_triggered
                or profit_protect_triggered
                or trailing_stop_triggered
                or donchian_failure_triggered
                or trend_exit_triggered
            ),
            reason="no_exit_signal",
            actual={
                "stop_triggered": stop_triggered,
                "partial_take_profit_triggered": partial_take_profit_triggered,
                "profit_protect_triggered": profit_protect_triggered,
                "trailing_stop_triggered": trailing_stop_triggered,
                "donchian_failure_triggered": donchian_failure_triggered,
                "trend_exit_triggered": trend_exit_triggered,
            },
            required={"exit_triggered": True},
        ),
        FunnelStep(
            stage="amount",
            passed=estimated_exit_amount >= min_order_amount,
            reason="sell_amount_too_small",
            actual={"sell_amount": estimated_exit_amount},
            required={"min_order_amount": min_order_amount},
        ),
        FunnelStep(
            stage="order_value",
            passed=sell_order_value_quote > min_sell_order_value,
            reason="sell_order_value_too_small",
            actual={"sell_order_value_quote": sell_order_value_quote},
            required={"min_sell_order_value": min_sell_order_value},
        ),
    ]
