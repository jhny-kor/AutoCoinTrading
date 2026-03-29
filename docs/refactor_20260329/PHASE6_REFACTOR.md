# 2026-03-29 6차 리팩토링

## 목표

- 퍼널 step 생성기와 포트폴리오 배분 래퍼를 실제 런타임 코드에 연결
- 실제 디렉토리 재배치 이후에도 기존 명령 경로를 유지하는 호환 래퍼를 추가

## 신설 경로

- `core/strategy/funnels.py`
- `core/risk/allocation.py`

## 반영 내용

- 알트 봇
  - `build_alt_entry_steps`
  - `build_alt_exit_steps`
  - `build_alt_allocation`
  를 실제로 연결

- BTC 봇
  - `build_btc_allocations`
  를 실제로 연결

- 루트 호환 래퍼 추가
  - `strategy_settings.py`
  - `btc_trend_settings.py`
  - `portfolio_allocator.py`
  - `market_regime_guard.py`
  - `state_recovery.py`
  - `analyze_logs.py`
  - `analyze_strategy_logs.py`
  - `telegram_notifier.py`
  - `analysis_log_collector.py`
  - `telegram_command_listener.py`
  - 기타 tools/reporting 진입점

## 효과

- 실제 런타임이 공통 생성기/래퍼를 사용하게 되어 리팩토링이 구조상만이 아니라 실행상으로도 반영됨
- 기존 명령과 import 호환성이 유지되어 운영 중단 없이 디렉토리 재배치 가능

## 후속 작업

- `core/logging/metrics.py` 로 알트/BTC common metrics builder 분리
- BTC 퍼널 step 생성기 공통화 완료
- 루트 호환 래퍼 유지 정책 별도 문서화
