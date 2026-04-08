"""
수정 요약
- 2026-04-08: 비교 코멘트에서 `확인필요` 상태를 추출하고 웹이 사용할 삭제 액션 메타데이터를 함께 기록하도록 확장
- reports/backtest_batches 아래 batch/diff 결과를 스캔해 backtest_registry.json 을 자동 갱신하는 도구를 추가
- batch_summary, diff_summary, 비교 대상 경로, 심볼 목록을 함께 기록하도록 구성

백테스트 레지스트리 갱신 도구

- 목적: 실험 결과를 폴더 탐색 없이 한 파일에서 찾을 수 있게 인덱싱한다.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKTEST_BATCH_DIR = ROOT_DIR / "reports" / "backtest_batches"
BACKTEST_SINGLE_DIR = ROOT_DIR / "reports" / "backtests"
REGISTRY_PATH = ROOT_DIR / "reports" / "backtest_registry.json"
REVIEW_HINT_KEYWORDS = (
    "확인",
    "불일치",
    "차이",
    "점검",
    "리플레이 가정",
)


def safe_read_json(path: Path) -> Any:
    """JSON 파일을 안전하게 읽는다."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def should_mark_review_needed(text: str) -> bool:
    """비교 코멘트에서 수동 확인 필요 여부를 판정한다."""
    normalized = str(text or "").strip()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in REVIEW_HINT_KEYWORDS)


def build_delete_action(path: Path, review_required: bool) -> dict[str, Any] | None:
    """웹이 사용할 삭제 액션 메타데이터를 만든다."""
    if not review_required:
        return None
    return {
        "label": "삭제",
        "enabled": True,
        "handler": "tools/delete_backtest_entry.py",
        "target_path": str(path),
        "target_type": "directory",
    }


def collect_review_comments_from_comparison(comparison: Any) -> list[str]:
    """comparison payload 안의 확인 필요 코멘트를 모은다."""
    if not isinstance(comparison, dict):
        return []
    comments = comparison.get("comments", [])
    if not isinstance(comments, list):
        return []
    review_comments: list[str] = []
    for item in comments:
        text = str(item or "").strip()
        if text and should_mark_review_needed(text):
            review_comments.append(text)
    return review_comments


def collect_batch_review_comments(rows: Any) -> list[str]:
    """배치 행 전체에서 확인 필요 코멘트를 모은다."""
    if not isinstance(rows, list):
        return []
    review_comments: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        review_comments.extend(collect_review_comments_from_comparison(row.get("comparison")))
    return review_comments


def build_batch_entry(batch_dir: Path) -> dict[str, Any] | None:
    """batch_summary 기준 레지스트리 항목을 만든다."""
    summary_path = batch_dir / "batch_summary.json"
    payload = safe_read_json(summary_path)
    if not isinstance(payload, dict):
        return None
    rows = payload.get("rows", [])
    review_comments = collect_batch_review_comments(rows)
    review_required = bool(review_comments)
    symbols: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol", "")).strip()
            if symbol:
                symbols.append(symbol)
    entry = {
        "type": "batch",
        "name": batch_dir.name,
        "label": payload.get("label"),
        "created_at": payload.get("created_at"),
        "path": str(batch_dir),
        "summary_path": str(summary_path),
        "since": payload.get("since"),
        "until": payload.get("until"),
        "symbols": sorted(set(symbols)),
        "review_required": review_required,
        "review_status": "확인필요" if review_required else "정상",
        "review_reasons": review_comments[:10],
    }
    delete_action = build_delete_action(batch_dir, review_required)
    if delete_action is not None:
        entry["actions"] = {"delete": delete_action}
    return entry


def build_single_backtest_entry(backtest_dir: Path) -> dict[str, Any] | None:
    """summary.json 기준 단일 백테스트 항목을 만든다."""
    summary_path = backtest_dir / "summary.json"
    payload = safe_read_json(summary_path)
    if not isinstance(payload, dict):
        return None
    symbol = str(payload.get("symbol", "")).strip()
    comparison_comments = collect_review_comments_from_comparison(
        safe_read_json(backtest_dir / "comparison.json")
    )
    review_required = bool(comparison_comments)
    entry = {
        "type": "single",
        "name": backtest_dir.name,
        "label": payload.get("label"),
        "created_at": payload.get("created_at") or datetime.fromtimestamp(backtest_dir.stat().st_mtime).isoformat(),
        "path": str(backtest_dir),
        "summary_path": str(summary_path),
        "exchange_name": payload.get("exchange_name"),
        "strategy_type": payload.get("strategy_type"),
        "symbols": [symbol] if symbol else [],
        "review_required": review_required,
        "review_status": "확인필요" if review_required else "정상",
        "review_reasons": comparison_comments[:10],
    }
    delete_action = build_delete_action(backtest_dir, review_required)
    if delete_action is not None:
        entry["actions"] = {"delete": delete_action}
    return entry


def build_diff_entry(diff_dir: Path) -> dict[str, Any] | None:
    """diff_summary 기준 레지스트리 항목을 만든다."""
    summary_path = diff_dir / "diff_summary.json"
    payload = safe_read_json(summary_path)
    if not isinstance(payload, list):
        return None

    markdown_path = diff_dir / "diff_summary.md"
    before_dir = None
    after_dir = None
    if markdown_path.exists():
        for line in markdown_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- before: `"):
                before_dir = line.split("`", 2)[1]
            elif line.startswith("- after: `"):
                after_dir = line.split("`", 2)[1]

    symbols: list[str] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key", "")).strip()
        if "::" not in key:
            continue
        _, symbol = key.split("::", 1)
        if symbol:
            symbols.append(symbol)

    entry = {
        "type": "diff",
        "name": diff_dir.name,
        "created_at": datetime.fromtimestamp(diff_dir.stat().st_mtime).isoformat(),
        "path": str(diff_dir),
        "diff_path": str(summary_path),
        "before_dir": before_dir,
        "after_dir": after_dir,
        "symbols": sorted(set(symbols)),
        "review_required": False,
        "review_status": "정상",
        "review_reasons": [],
    }
    return entry


def build_registry_entries(base_dir: Path) -> list[dict[str, Any]]:
    """레지스트리 전체 항목을 만든다."""
    entries: list[dict[str, Any]] = []
    if not base_dir.exists():
        return entries

    for child in sorted((path for path in base_dir.iterdir() if path.is_dir()), reverse=True):
        single_entry = build_single_backtest_entry(child)
        if single_entry is not None:
            entries.append(single_entry)
            continue
        batch_entry = build_batch_entry(child)
        if batch_entry is not None:
            entries.append(batch_entry)
            continue
        diff_entry = build_diff_entry(child)
        if diff_entry is not None:
            entries.append(diff_entry)
    return entries


def build_all_registry_entries() -> list[dict[str, Any]]:
    """단일 백테스트와 배치/비교 결과를 합쳐 전체 레지스트리를 만든다."""
    entries = build_registry_entries(BACKTEST_SINGLE_DIR)
    entries.extend(build_registry_entries(BACKTEST_BATCH_DIR))
    entries.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return entries


def write_registry(path: Path, entries: list[dict[str, Any]]) -> None:
    """레지스트리 파일을 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(),
        "entries": entries,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="backtest batch/diff 결과 레지스트리 갱신")
    parser.add_argument("--base-dir", default=str(BACKTEST_BATCH_DIR))
    parser.add_argument("--output", default=str(REGISTRY_PATH))
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    args = build_parser().parse_args(argv)
    base_dir = Path(args.base_dir)
    output_path = Path(args.output)
    if base_dir.resolve() == BACKTEST_BATCH_DIR.resolve():
        entries = build_all_registry_entries()
    else:
        entries = build_registry_entries(base_dir)
    write_registry(output_path, entries)
    print(f"레지스트리 갱신 완료: {output_path}")
    print(f"- 항목 수: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
