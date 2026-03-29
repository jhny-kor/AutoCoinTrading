# 오더북 미시구조 / 시장 구조 레이어 설계안

기준 날짜: 2026-03-28

이 문서는 현재 `MA/EMA + ATR + volume + HTF filter` 중심 전략 위에

- `오더북 미시구조 레이어`
- `시장 구조 레이어`

를 추가하는 설계안을 정리한 문서입니다.

이번 문서의 목적은 `바로 구현`이 아니라, 현재 운영과 비교했을 때

- 어디가 달라지는지
- 어떤 부분은 그대로 두는지
- 실제 운영 리스크가 커지는지
- 도입 순서를 어떻게 가져가는지

를 먼저 분명히 하는 것입니다.

## 1. 현재 운영 기준

현재 전략 핵심

- 알트
  - 1분봉 MA 돌파 기반
  - 거래량, 변동성, HTF, 쿨다운, 포트폴리오 제한
  - 부분익절, 부분손절, 순익 보호, 브레이크이븐 가드
- BTC
  - 5분봉 EMA + 15분봉 확인
  - ATR, 거래량, EMA spread, confirm filter
  - 부분익절, 순익 보호, 트레일링, 피라미딩

현재 강점

- 구조화 로그가 강함
- 체결 품질, MFE/MAE, 손익 기록이 있음
- 최근에는 보수형/중간형/혼합형 세트까지 비교 가능한 상태

현재 한계

- 진입 신호의 마지막 품질 판정이 차트 기반 요소 위주
- 같은 신호라도 `얇은 호가`, `실패 돌파`, `후반부 과열 추세`를 충분히 분리하지 못함
- 실거래가 백테스트보다 손절 쪽으로 밀리는 심볼이 존재함

## 2. 이번 설계안의 핵심 원칙

새 레이어를 넣어도 아래는 그대로 유지합니다.

- MA/EMA 기반 기본 엔진 유지
- ATR/volume/HTF 필터 유지
- 손절 우선 규칙 유지
- 저시드 운영 전제 유지
- 공통 전략 구조 유지

즉 설계 방향은

- 기존 신호를 폐기하지 않음
- 기존 신호 위에 `품질 판정 레이어`를 추가
- “진입을 더 똑똑하게 걸러내는 것”에 집중

입니다.

## 3. 오더북 미시구조 레이어 설계안

### 3.1 목표

이 레이어의 목표는 `가격 방향 예측`이 아닙니다.

목표는 아래 두 가지입니다.

- 체결 직전 불리한 구간 회피
- 같은 매수 신호라도 `호가 품질이 나쁜 구간` 차단

즉 “사도 될까?”보다

- “지금 이 호가 상태에서 사면 불리한가?”

를 보는 필터입니다.

### 3.2 현재 이미 있는 입력값

현재 분석 수집기에서 이미 쌓는 값

- `spread_pct`
- `bid_ask_size_imbalance`
- `depth_size_imbalance_3`
- `depth_size_imbalance_5`
- `bid_depth_notional_3`
- `ask_depth_notional_3`
- `bid_depth_notional_5`
- `ask_depth_notional_5`
- `buy_sweep_slippage_bps`
- `sell_sweep_slippage_bps`

즉 이 레이어는 데이터 수집부터 새로 할 필요가 없습니다.

### 3.3 추천 배치 위치

진입 퍼널 안에서 아래 순서가 적절합니다.

1. 기본 신호
2. 이격도
3. 거래량
4. 변동성 / ATR
5. HTF
6. 시장 구조
7. 오더북 미시구조
8. 쿨다운
9. 포트폴리오 예산
10. 주문 요청

여기서 미시구조는 `마지막 진입 품질 게이트` 역할입니다.

### 3.4 1차 필터 규칙

1차는 가장 해석이 쉬운 필드만 씁니다.

- `spread_pct <= max_spread_pct`
- `buy_sweep_slippage_bps <= max_buy_sweep_slippage_bps`
- `depth_size_imbalance_3 >= min_depth_imbalance_3`
- `bid_depth_notional_3 >= min_bid_depth_notional_3`

추천 이유

- `spread` 는 체결 직후 손실과 바로 연결됨
- `sweep slippage` 는 얇은 호가 추격 진입을 걸러줌
- `depth imbalance` 는 최소한의 매수 우위 확인
- `bid depth notional` 은 너무 얕은 책을 피하게 해줌

### 3.5 추천 env 설계

```env
STRATEGY_ENABLE_MICROSTRUCTURE_FILTER=true
STRATEGY_MICROSTRUCTURE_REQUIRE_ALL=false
STRATEGY_MAX_SPREAD_PCT=0.020
STRATEGY_MAX_SPREAD_PCT_MAP=ETH/KRW:0.020,XRP/KRW:0.030,ETH/USDT:0.015,XRP/USDT:0.020
STRATEGY_MAX_BUY_SWEEP_SLIPPAGE_BPS=8
STRATEGY_MAX_BUY_SWEEP_SLIPPAGE_BPS_MAP=ETH/KRW:10,XRP/KRW:12,ETH/USDT:6,XRP/USDT:8
STRATEGY_MIN_DEPTH_IMBALANCE_3=0.95
STRATEGY_MIN_DEPTH_IMBALANCE_3_MAP=ETH/KRW:0.98,XRP/KRW:1.00
STRATEGY_MIN_BID_DEPTH_NOTIONAL_3=100000
STRATEGY_MIN_BID_DEPTH_NOTIONAL_3_MAP=ETH/KRW:300000,XRP/KRW:200000,ETH/USDT:300,XRP/USDT:200
```

### 3.6 추천 reason code

- `microstructure_ok`
- `spread_too_wide`
- `buy_sweep_slippage_too_high`
- `depth_imbalance_too_weak`
- `bid_depth_too_shallow`
- `microstructure_snapshot_missing`
- `microstructure_snapshot_stale`

### 3.7 shadow mode 도입 순서

1차

- 실제 차단 없음
- 로그만 남김

2차

- `spread_too_wide`
- `buy_sweep_slippage_too_high`

만 실제 차단

3차

- `depth imbalance`
- `depth notional`

추가

이렇게 가야 갑자기 거래가 0건이 되는 걸 막을 수 있습니다.

## 4. 시장 구조 레이어 설계안

### 4.1 목표

이 레이어의 목표는

- “같은 MA/EMA 신호라도 어떤 장에서 나온 신호인지 구분”

하는 것입니다.

즉 신호 자체보다 `신호가 발생한 장세의 질`을 보는 상위 판정입니다.

### 4.2 현재 구조와의 관계

현재도 레짐 분류는 이미 있습니다.

- `LOW_ENERGY`
- `CHOPPY`
- `BREAKOUT_ATTEMPT`
- `TRENDING`
- `OVERHEATED`

하지만 이건 거래 차단용 guard 성격이 강합니다.

새 구조 레이어는 그보다 더 실전적인 판정이 필요합니다.

예:

- 추세 지속
- 확인된 돌파
- 실패 돌파 위험
- 박스권 잡음
- 추세 후반 과열
- 눌림 진입 구간

### 4.3 추천 구조 상태

- `trend_continuation`
- `breakout_confirmed`
- `failed_breakout_risk`
- `range_chop`
- `late_trend_exhaustion`
- `pullback_entry_zone`

### 4.4 상태 정의 초안

`trend_continuation`

- HTF bullish
- 현재가가 MA 위
- 최근 스윙 고점/저점이 상승

`breakout_confirmed`

- 최근 n봉 고점 돌파
- 돌파 후 hold bars 유지
- volume 조건 통과

`failed_breakout_risk`

- 최근 고점 돌파 시도 후 다시 범위 안 복귀
- range 상단에서 거래량 부족 또는 미시구조 나쁨

`range_chop`

- 고점/저점 갱신 부재
- 평균 절대 변화율 낮음
- 신호는 있으나 구조가 탁함

`late_trend_exhaustion`

- 추세는 살아 있지만 과열
- 고점 갱신 둔화
- 추격 진입 위험

`pullback_entry_zone`

- 상위 추세 상승 유지
- 최근 조정 후 회복 직전
- 추세 재개 후보

### 4.5 추천 env 설계

```env
STRATEGY_ENABLE_MARKET_STRUCTURE_FILTER=true
STRATEGY_STRUCTURE_SWING_LOOKBACK=10
STRATEGY_STRUCTURE_BREAKOUT_LOOKBACK=20
STRATEGY_STRUCTURE_BREAKOUT_HOLD_BARS=3
STRATEGY_STRUCTURE_RANGE_TOP_PCT=80
STRATEGY_STRUCTURE_RANGE_BOTTOM_PCT=20
STRATEGY_STRUCTURE_FAILED_BREAKOUT_RETRACE_PCT=0.12
STRATEGY_STRUCTURE_MIN_HIGHER_LOW_COUNT=2
STRATEGY_STRUCTURE_MIN_HIGHER_HIGH_COUNT=2
STRATEGY_STRUCTURE_ENABLE_FAST_EXIT_ON_FAILED_BREAKOUT=true
```

### 4.6 추천 reason code

- `structure_ok`
- `range_chop_blocks_entry`
- `failed_breakout_risk_blocks_entry`
- `late_trend_exhaustion_blocks_entry`
- `breakout_confirmed_allows_entry`
- `pullback_entry_zone_allows_entry`
- `structure_snapshot_missing`

### 4.7 상태별 action

`trend_continuation`

- 진입 허용
- 기본 청산 유지

`breakout_confirmed`

- 진입 허용
- 필요 시 비중 소폭 확대 가능

`failed_breakout_risk`

- 신규 진입 차단
- 보유 중이면 `profit_protect` 우선

`range_chop`

- 신규 진입 차단

`late_trend_exhaustion`

- 신규 진입 차단
- 보유 중이면 브레이크이븐 더 빨리

`pullback_entry_zone`

- 진입 허용
- 단, 미시구조 기준은 더 엄격히

## 5. 현재 운영과 무엇이 달라지는가

### 5.1 전략 엔진

현재

- MA/EMA 신호가 핵심
- ATR/volume/HTF 가 주요 필터

설계안 적용 후

- MA/EMA 신호는 그대로 핵심
- ATR/volume/HTF 도 그대로 유지
- 다만 그 위에
  - 시장 구조 레이어
  - 미시구조 레이어
  - 가 추가됨

결론

- `전략이 크게 바뀌는 것`은 아님
- `신호를 승인하는 최종 단계`가 더 늘어나는 구조

### 5.2 운영 로그

현재

- trend, distance, volume, volatility, cooldown 등 위주

설계안 적용 후

- `market_structure`
- `microstructure`

stage 가 추가

결론

- 기존 로그 체계와 충돌 없음
- 오히려 병목 원인 추적이 쉬워짐

### 5.3 거래 빈도

현재

- 이미 보수적

설계안 적용 후

- 초기에는 더 줄어들 가능성 큼

결론

- shadow mode 없이 바로 차단 적용하면 과도하게 보수화될 수 있음
- 반드시 shadow mode -> 제한적 차단 -> 확대 순서 필요

### 5.4 리스크 관리

현재

- 손절, 부분손절, 브레이크이븐, 순익 보호, 일일 손실 제한 존재

설계안 적용 후

- 리스크 관리 철학은 유지
- 다만 손절 이후가 아니라 `진입 전` 품질 통제가 더 강해짐

결론

- 운영 철학은 그대로
- 진입 품질만 강화

### 5.5 백테스트/비교

현재

- MA/EMA/ATR 기반 규칙은 백테스트 가능

설계안 적용 후

- 미시구조 필드는 분석 로그 스냅샷까지 함께 가져와야 함
- 시장 구조 상태도 리플레이 계산에 추가해야 함

결론

- 백테스트 복잡도는 증가
- 하지만 현재 구조라면 확장 가능

## 6. 크게 달라지는 부분 / 크게 안 달라지는 부분

크게 달라지는 부분

- 진입 승인 퍼널이 길어짐
- 차단 이유가 더 세밀해짐
- 저품질 체결 구간을 더 많이 피하게 됨

크게 안 달라지는 부분

- 기본 진입 엔진은 MA/EMA 기반 유지
- ATR/volume/HTF 필터 유지
- 손절 우선 규칙 유지
- 저시드 운영 원칙 유지
- 공통 `.env` 기반 운영 유지

## 7. 추천 구현 순서

1. `market_structure_filter.py`
  - 상태 계산만
  - shadow mode
2. `/analysis`
  - 구조 상태 출력
3. `microstructure_filter.py`
  - spread, sweep slippage 만 shadow mode
4. 실차단 1차
  - `failed_breakout_risk`
  - `spread_too_wide`
  - `buy_sweep_slippage_too_high`
5. 이후 심볼별 map 세분화

## 8. 추천 판단

가장 먼저 넣을 것은 `시장 구조 레이어`입니다.

이유

- 현재 레짐 가드와 자연스럽게 이어짐
- 기존 차트 기반 전략과 충돌이 적음
- 해석이 쉬움
- 백테스트와 비교도 상대적으로 단순

두 번째는 `오더북 미시구조 레이어`입니다.

이유

- 이미 데이터는 수집 중
- 체결 품질과 직접 연결
- 저시드 단타에 특히 유효

세 번째가 `ML` 입니다.

이유

- 지금은 아직 규칙 기반 확장만으로도 개선 여지가 큼
- ML은 그 다음 단계의 메타 필터가 더 적절

## 9. 다음 문서화 후보

다음 단계에서 필요하면 아래도 바로 만들 수 있습니다.

- `.env.example` 키 추가안
- `reason code` 표
- `shadow mode` 체크리스트
- `구현 순서별 TODO`
