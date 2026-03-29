# 2026-03-29 5차 리팩토링

## 목표

- BTC 보유 포지션 평가 블록 중복 제거
- 손절가/익절가 계산, 수익률/순익률 계산, 부분익절/트레일링 활성화 판단을 공통화

## 신설 경로

- `core/strategy/btc_position.py`

## 반영 내용

- `build_btc_exit_prices`
  - BTC 손절가/익절가 계산 공통화

- `evaluate_btc_open_position`
  - BTC 보유 중 성능 계산 공통화
  - `pnl_pct`, `mfe_pct`, `mae_pct`, 순익률, 부분익절 조건, 트레일링 활성화 여부, 일시조정 보유 판단을 한 곳에서 계산

- 적용 파일
  - `okx_btc_ema_trend_bot.py`
  - `upbit_btc_ema_trend_bot.py`

## 효과

- BTC 두 봇의 가장 큰 중복 블록이 공통 함수로 이동
- 부분익절/트레일링/성능 계산 로직 수정 지점이 한 곳으로 줄어듦

## 아직 남은 것

- 퍼널 step 정의
- 포트폴리오 배분 로그와 주문 전 보조 계산
- 봇 진입점 자체의 디렉토리 재배치
