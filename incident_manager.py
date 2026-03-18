"""
수정 요약
- 텔레그램 승인형 복구에 쓸 에러 인시던트 저장소를 추가
- 동일 에러를 짧은 시간 안에 묶어 건수와 마지막 발생 시각을 누적 관리하도록 구성
- 버튼 클릭 후 상태를 `ignored`, `restart_requested`, `fix_requested` 등으로 업데이트할 수 있도록 지원
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


INCIDENTS_PATH = Path("logs") / "telegram_incidents.json"


def _load_incidents(path: Path = INCIDENTS_PATH) -> list[dict[str, Any]]:
    """인시던트 목록을 읽는다."""
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _save_incidents(incidents: list[dict[str, Any]], path: Path = INCIDENTS_PATH) -> None:
    """인시던트 목록을 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(incidents, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def register_incident(
    *,
    exchange_name: str,
    symbol: str,
    detail: str,
    dedupe_window_sec: int = 300,
    path: Path = INCIDENTS_PATH,
) -> dict[str, Any]:
    """에러 인시던트를 등록하고 최신 레코드를 반환한다."""
    incidents = _load_incidents(path)
    now_ts = time.time()
    signature = f"{exchange_name}|{symbol}|{detail.strip()}"

    for incident in reversed(incidents):
        if incident.get("signature") != signature:
            continue
        last_seen_ts = float(incident.get("last_seen_ts", 0.0) or 0.0)
        if (now_ts - last_seen_ts) > dedupe_window_sec:
            break
        incident["count"] = int(incident.get("count", 1)) + 1
        incident["last_seen_ts"] = now_ts
        incident["last_seen_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now_ts))
        _save_incidents(incidents, path)
        return incident

    incident_id = f"inc_{int(now_ts)}_{len(incidents) + 1}"
    record = {
        "id": incident_id,
        "signature": signature,
        "exchange_name": exchange_name,
        "symbol": symbol,
        "detail": detail,
        "count": 1,
        "status": "open",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now_ts)),
        "created_ts": now_ts,
        "last_seen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now_ts)),
        "last_seen_ts": now_ts,
        "last_action": None,
    }
    incidents.append(record)
    _save_incidents(incidents, path)
    return record


def find_incident(incident_id: str, path: Path = INCIDENTS_PATH) -> dict[str, Any] | None:
    """ID 기준 인시던트를 찾는다."""
    for incident in _load_incidents(path):
        if incident.get("id") == incident_id:
            return incident
    return None


def update_incident_status(
    incident_id: str,
    *,
    status: str,
    action: str,
    path: Path = INCIDENTS_PATH,
) -> dict[str, Any] | None:
    """인시던트 상태와 마지막 액션을 갱신한다."""
    incidents = _load_incidents(path)
    now_text = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
    for incident in incidents:
        if incident.get("id") != incident_id:
            continue
        incident["status"] = status
        incident["last_action"] = action
        incident["updated_at"] = now_text
        _save_incidents(incidents, path)
        return incident
    return None
