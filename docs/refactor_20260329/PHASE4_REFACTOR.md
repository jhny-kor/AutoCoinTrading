# 2026-03-29 4차 리팩토링

## 목표

- 알트 청산 보호 계산 중복 제거
- 수익률, 순익률, 브레이크이븐, 순익 보호 익절 계산을 공통화

## 신설 경로

- `core/risk/alt_exit.py`

## 반영 내용

- `compute_alt_position_metrics`
  - 알트 포지션 보유 중 `pnl_pct`, `mfe_pct`, `mae_pct`, 순익 추정 계산 공통화

- `compute_alt_exit_decisions`
  - 최소 익절률, 손절, 순익 보호 익절, 브레이크이븐 가드, 추정 매도 비율 계산 공통화

- 적용 파일
  - `ma_crossover_bot.py`
  - `upbit_ma_crossover_bot.py`

## 효과

- 알트 청산 보호 로직이 한 곳으로 모여 ETH/XRP/PI 계열 조정 지점이 줄어듦
- 수익률/순익률 계산과 청산 조건 계산이 분리돼 읽기 쉬워짐

## 아직 남은 것

- BTC 보유 포지션 평가와 부분익절/트레일링 활성화 블록은 아직 각 BTC 봇 안에 남아 있음
- 알트/업비트 쪽 포트폴리오 배분과 퍼널 정의는 여전히 각 봇 내부에 있음
