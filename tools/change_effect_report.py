"""
수정 요약
- 변경 효과 자동 비교 리포트를 터미널에서 실행하는 CLI 를 추가했다.

사용 예시
- .venv/bin/python tools/change_effect_report.py
- .venv/bin/python tools/change_effect_report.py --hours 24 --write
- .venv/bin/python tools/change_effect_report.py --change-at 2026-05-06T13:00:00+09:00
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.change_effect_report import (
    build_change_effect_report,
    format_change_effect_text,
    parse_timestamp,
    write_report,
)


def main() -> None:
    """CLI 엔트리 포인트."""
    parser = argparse.ArgumentParser(description="변경 효과 자동 비교 리포트")
    parser.add_argument(
        "--change-at",
        default="",
        help="비교 기준 시각. 비우면 최신 git commit 시각을 사용",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=12.0,
        help="변경 전후 비교 시간",
    )
    parser.add_argument(
        "--strategy-log-root",
        default="structured_logs/live",
        help="구조화 전략 로그 루트",
    )
    parser.add_argument(
        "--trade-log-root",
        default="trade_logs",
        help="체결 이력 로그 루트",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="reports/change_effect 아래 JSON 결과를 저장",
    )
    args = parser.parse_args()

    change_at = parse_timestamp(args.change_at) if args.change_at else None
    report = build_change_effect_report(
        change_at=change_at,
        hours=args.hours,
        strategy_log_root=Path(args.strategy_log_root),
        trade_log_root=Path(args.trade_log_root),
    )
    print(format_change_effect_text(report))
    if args.write:
        path = write_report(report)
        print(f"\n저장 완료: {path}")


if __name__ == "__main__":
    main()
