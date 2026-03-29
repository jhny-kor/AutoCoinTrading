"""
작업 요약
- 알트/BTC 공통 metrics 조립을 builder 함수로 분리했다.
- 공통 필드 구조를 유지하면서 봇 파일의 metrics 블록 중복을 줄였다.
"""

from __future__ import annotations


def build_alt_common_metrics(**kwargs) -> dict:
    return dict(kwargs)


def build_btc_common_metrics(**kwargs) -> dict:
    return dict(kwargs)
