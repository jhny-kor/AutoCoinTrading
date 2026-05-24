"""
수정 요약
- 2026-05-24: 거래소 API 허용 IP 오류를 같은 원인으로 정규화하고, ignored 인시던트는 계속 묶어 텔레그램 반복 알림을 줄이도록 보강
- 텔레그램 승인형 복구에 쓸 에러 인시던트 저장소를 추가
- 동일 에러를 짧은 시간 안에 묶어 건수와 마지막 발생 시각을 누적 관리하도록 구성
- 버튼 클릭 후 상태를 `ignored`, `restart_requested`, `fix_requested` 등으로 업데이트할 수 있도록 지원
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any


INCIDENTS_PATH = Path("logs") / "telegram_incidents.json"
IP_ADDRESS_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


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


def normalize_incident_detail_for_signature(detail: str) -> str:
    """같은 운영 원인을 같은 인시던트로 묶을 수 있게 상세 문자열을 정규화한다."""
    compact = " ".join(detail.strip().split())
    lowered = compact.lower()

    if "no_authorization_ip" in lowered or "this is not a verified ip" in lowered:
        return "upbit_ip_authorization_required"

    if "not included in your api key" in lowered and "ip whitelist" in lowered:
        ip_match = IP_ADDRESS_RE.search(compact)
        ip_suffix = f":{ip_match.group(0)}" if ip_match else ""
        return f"okx_ip_whitelist_required{ip_suffix}"

    return compact


def _incident_matches_signature(
    incident: dict[str, Any],
    *,
    exchange_name: str,
    symbol: str,
    signature: str,
    normalized_detail: str,
) -> bool:
    """기존 raw signature 와 신규 정규화 signature 를 모두 비교한다."""
    if incident.get("signature") == signature:
        return True
    if incident.get("exchange_name") != exchange_name or incident.get("symbol") != symbol:
        return False
    existing_detail = str(incident.get("detail", ""))
    return normalize_incident_detail_for_signature(existing_detail) == normalized_detail


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
    normalized_detail = normalize_incident_detail_for_signature(detail)
    signature = f"{exchange_name}|{symbol}|{normalized_detail}"

    for incident in reversed(incidents):
        if not _incident_matches_signature(
            incident,
            exchange_name=exchange_name,
            symbol=symbol,
            signature=signature,
            normalized_detail=normalized_detail,
        ):
            continue
        last_seen_ts = float(incident.get("last_seen_ts", 0.0) or 0.0)
        status = str(incident.get("status", "open"))
        if status != "ignored" and (now_ts - last_seen_ts) > dedupe_window_sec:
            break
        incident["count"] = int(incident.get("count", 1)) + 1
        incident["detail"] = detail
        incident["signature"] = signature
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
