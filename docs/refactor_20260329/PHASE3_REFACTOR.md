# 2026-03-29 3차 리팩토링

## 목표

- 포트폴리오/리스크 계산 중 반복도가 높은 부분을 공통화
- 일일 손실 제한과 동적 오버웨이트 자격 판정을 봇 파일 바깥으로 이동

## 신설 경로

- `core/risk/shared.py`

## 반영 내용

- `is_daily_loss_limit_reached`
  - 네 봇에서 공통으로 쓰는 일일 손실 제한 판정 이동

- `is_dynamic_bonus_eligible`
  - 알트/BTC 모두에서 쓰는 동적 오버웨이트 자격 판정 이동

- 적용 파일
  - `ma_crossover_bot.py`
  - `upbit_ma_crossover_bot.py`
  - `okx_btc_ema_trend_bot.py`
  - `upbit_btc_ema_trend_bot.py`

## 효과

- 리스크 계산식이 한 곳으로 모여 기본값 수정과 회귀 점검이 쉬워짐
- 포트폴리오 오버웨이트 자격 판정의 거래소/전략 간 일관성이 좋아짐

## 다음 단계

- 브레이크이븐/순익 보호/부분익절 세부 분기를 `core/risk` 또는 `core/strategy` 로 추가 이동
- `bots/` 디렉토리로 실행 진입점 분리
