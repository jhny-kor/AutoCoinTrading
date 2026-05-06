"""
수정 요약
- 미체결 후보 가상 추적 리포트를 터미널에서 실행하는 CLI 를 추가했다.

사용 예시
- .venv/bin/python tools/shadow_candidate_tracker.py
- .venv/bin/python tools/shadow_candidate_tracker.py --horizon-minutes 180 --write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.shadow_candidate_tracker import (
    build_shadow_candidate_report,
    format_shadow_candidate_text,
    write_report,
)


def main() -> None:
    """CLI 엔트리 포인트."""
    parser = argparse.ArgumentParser(description="미체결 후보 가상 추적 리포트")
    parser.add_argument(
        "--strategy-log-root",
        default="structured_logs/live",
        help="구조화 전략 로그 루트",
    )
    parser.add_argument(
        "--min-signal-score",
        type=float,
        default=50.0,
        help="후보로 볼 최소 신호 점수",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help="최근 며칠 로그를 읽을지 지정. 0이면 --hours 사용",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=6.0,
        help="--days 0일 때 최근 몇 시간 로그를 읽을지 지정",
    )
    parser.add_argument(
        "--min-effective-position-ratio",
        type=float,
        default=0.01,
        help="후보로 볼 최소 실효 매수 비중",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=int,
        default=300,
        help="같은 프로그램/심볼 후보 중복 제거 간격",
    )
    parser.add_argument(
        "--horizon-minutes",
        type=int,
        default=60,
        help="후보 이후 관찰 시간",
    )
    parser.add_argument(
        "--take-profit-pct",
        type=float,
        default=0.5,
        help="가상 익절 판정 수익률",
    )
    parser.add_argument(
        "--stop-loss-pct",
        type=float,
        default=0.8,
        help="가상 손절 판정 손실률",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="reports/shadow_candidates 아래 JSON 결과를 저장",
    )
    args = parser.parse_args()

    report = build_shadow_candidate_report(
        strategy_log_root=Path(args.strategy_log_root),
        recent_days=args.days,
        lookback_hours=args.hours,
        min_signal_score=args.min_signal_score,
        min_effective_position_ratio=args.min_effective_position_ratio,
        cooldown_seconds=args.cooldown_seconds,
        horizon_minutes=args.horizon_minutes,
        take_profit_pct=args.take_profit_pct,
        stop_loss_pct=args.stop_loss_pct,
    )
    print(format_shadow_candidate_text(report))
    if args.write:
        path = write_report(report)
        print(f"\n저장 완료: {path}")


if __name__ == "__main__":
    main()
