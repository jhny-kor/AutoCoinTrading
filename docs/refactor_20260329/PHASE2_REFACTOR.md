# 2026-03-29 2차 리팩토링

## 목표

- 알트/BTC 봇 내부의 반복 신호 계산과 포지션 초기화 로직을 공통 모듈로 분리
- 1차에서 만든 `core/execution`, `core/positions` 위에 `core/strategy` 를 추가해 다음 단계 리팩토링 기반 마련

## 신설 경로

- `core/strategy/alt.py`
- `core/strategy/btc.py`
- `core/positions/lifecycle.py`

## 반영 내용

- `core/strategy/alt.py`
  - 알트 골든/데드크로스 기반 신호 상태 계산
  - 추세 유지 진입 판단
  - 평균단가 대비 추가매수 허용 여부 계산

- `core/strategy/btc.py`
  - BTC EMA 정렬/이격/추세 유지 진입 상태 계산
  - 손절, 트레일링, 순익 보호, 추세 종료 플래그 계산

- `core/positions/lifecycle.py`
  - 알트 포지션 상태 초기화
  - BTC 포지션 상태 초기화

- `ma_crossover_bot.py`, `upbit_ma_crossover_bot.py`
  - 알트 신호 계산을 `core/strategy/alt.py` 로 위임
  - 포지션 정리 코드를 `core/positions/lifecycle.py` 로 위임

- `okx_btc_ema_trend_bot.py`, `upbit_btc_ema_trend_bot.py`
  - EMA 진입 상태 계산을 `core/strategy/btc.py` 로 위임
  - 포지션 종료 후 상태 초기화를 `core/positions/lifecycle.py` 로 위임

## 아직 남아 있는 것

- 브레이크이븐 가드, 부분익절 세부 분기, 포트폴리오 배분은 여전히 봇 파일 안에 남아 있음
- 거래소별 실행 진입점 파일은 아직 큼
- `bots/`, `reporting/`, `tools/` 디렉토리 재배치는 아직 하지 않음

## 다음 단계

- `core/strategy` 로 진입/청산 퍼널 전체를 더 이동
- `core/positions` 로 상태 갱신과 회복 로직을 더 이동
- 봇 파일을 실행 진입점 수준으로 축소
