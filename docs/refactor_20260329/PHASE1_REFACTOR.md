# 2026-03-29 1차 리팩토링

## 목표

- 거래소별 주문/조회 공통 로직을 봇 파일 바깥으로 이동
- 복구 불가 포지션 보류와 주문 실패 기록을 공통 처리로 정리
- 실행 흐름은 유지한 채 중복을 줄여 이후 2차 리팩토링 기반 마련

## 신설 경로

- `core/execution/common.py`
- `core/execution/okx.py`
- `core/execution/upbit.py`
- `core/positions/guards.py`

## 반영 내용

- `ma_crossover_bot.py`
  - OKX 설정/시세/잔고/주문 유틸을 `core/execution/okx.py`에 위임
  - 주문 실패 기록을 `core/execution/common.py`의 `log_order_failure`로 통일
  - 복구 불가 포지션 보류를 `core/positions/guards.py`의 `handle_unrecoverable_position`로 통일

- `upbit_ma_crossover_bot.py`
  - 업비트 설정/시세/잔고/주문 유틸을 `core/execution/upbit.py`에 위임
  - 주문 실패 기록을 `log_order_failure`로 통일
  - 복구 불가 포지션 보류를 `handle_unrecoverable_position`로 통일

- `okx_btc_ema_trend_bot.py`
  - 복구 불가 포지션 보류를 `handle_unrecoverable_position`로 통일
  - 주문 실패 기록을 `log_order_failure`로 통일

- `upbit_btc_ema_trend_bot.py`
  - 복구 불가 포지션 보류를 `handle_unrecoverable_position`로 통일
  - 주문 실패 기록을 `log_order_failure`로 통일

## 의도적으로 남겨둔 것

- 봇 실행 진입점 파일명과 `bot_manager.py` 구조는 유지
- 전략 판단식 자체는 변경하지 않음
- `ma_crossover_bot.py`, `upbit_ma_crossover_bot.py` 안의 일부 거래소 헬퍼 래퍼는 호환성을 위해 남김

## 다음 단계

- `core/strategy/`로 진입/청산 판단식 분리
- `core/positions/`로 상태 갱신과 포지션 라이프사이클 분리
- `bots/`, `reporting/`, `tools/`, `docs/` 실제 디렉토리 재배치
