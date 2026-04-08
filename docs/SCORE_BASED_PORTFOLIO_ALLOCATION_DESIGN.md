# Score 기반 동적 자본 배분 설계

현재 상태:

- 2026-04-09 기준 1차 구현 완료
- live 4봇, BTC add-on, backtest replay, example config 반영 완료
- 이후에는 가중치/버킷 튜닝이 중심 과제

## 목적

현재 포트폴리오 배분은

- 기본 목표 비중 `BTC / ETH / XRP`
- 레짐 스케일
- BTC 레짐 / BTC ATR 스케일
- 제한적 dynamic overweight

중심으로 동작합니다.

다음 단계 목표는 `좋은 심볼은 조금 더`, `안 좋은 심볼은 더 적게`를
`점수(score)` 기반으로 더 일관되게 반영하는 것입니다.

핵심 원칙은 아래와 같습니다.

- 확대보다 축소를 우선합니다.
- 낮은 시드머니 테스트 상황을 기준으로 과도한 비중 확대를 피합니다.
- 점수는 진입 신호 품질과 실행 품질을 함께 반영합니다.
- 최종 비중 변화는 좁은 범위에서만 허용합니다.

---

## 현재 구조 한계

현재 배분은 아래 요소가 분산돼 있습니다.

- 전략 점수: `signal_score`
- 레짐 기반 축소: `regime_position_scale`
- BTC 상태 기반 축소: `btc_regime_position_scale`, `btc_atr_position_scale`
- 제한적 overweight: `dynamic_bonus_eligible`

이 구조의 장점은 단순하고 안전하다는 점입니다.

하지만 한계도 있습니다.

- `좋은 심볼` 판단이 `strong signal + volume + trend` 수준에 머뭅니다.
- `나쁜 심볼` 판단은 여러 필터에 흩어져 있어 한 번에 설명하기 어렵습니다.
- 현재 최종 비중이 어떤 근거로 결정됐는지 직관적으로 추적하기 어렵습니다.
- 실거래와 백테스트 비교 시, 비중 변화 이유를 하나의 점수로 설명하기 어렵습니다.

---

## 설계 목표

score 기반 동적 배분은 아래를 만족해야 합니다.

1. 기존 목표 비중 체계를 유지
2. 기존 레짐 스케일 구조와 충돌하지 않음
3. 거래소별 차이 반영 가능
4. 로그에서 `왜 이 비중이 나왔는지` 바로 설명 가능
5. 과최적화 방지를 위해 변동 범위를 제한

즉 완전 자유 배분이 아니라,
`기본 목표 비중 x 품질 점수 기반 스케일`
구조로 가는 것이 적절합니다.

---

## 제안 구조

최종 진입 비중은 아래처럼 계산합니다.

`final_position_ratio = base_position_ratio x regime_scale x btc_context_scale x score_scale`

여기서

- `base_position_ratio`
  - 심볼별 기본 진입 비중
- `regime_scale`
  - 현재 심볼 레짐 기반 스케일
- `btc_context_scale`
  - BTC 레짐, BTC ATR 기반 스케일
- `score_scale`
  - 새로 도입할 품질 점수 기반 스케일

추천 범위:

- `score_scale` 하한: `0.60`
- `score_scale` 상한: `1.10`

즉 점수가 좋아도 `+10%` 정도만 확대,
점수가 나쁘면 `-40%` 정도까지 축소하는 보수형 구조입니다.

---

## Score 구성

점수는 `0 ~ 100` 범위로 계산합니다.

추천 구성은 아래 4개 축입니다.

### 1. Signal Score

기존 전략이 이미 계산하는 `signal_score`를 그대로 사용합니다.

- 알트: RSI, MACD, slope, gap 기반 점수
- BTC: EMA spread, RSI, BB width, slope 기반 점수

이 축은 가장 큰 비중을 둡니다.

권장 비중:

- `40%`

### 2. Market Quality Score

시장 상태 자체가 지금 진입에 적합한지 반영합니다.

입력 후보:

- `volume_ratio`
- `avg_abs_change_pct`
- `htf_bullish`
- `symbol_regime`
- `low_energy_guard_active`

예시 해석:

- `TRENDING`, `BREAKOUT_ATTEMPT`면 가산점
- `LOW_ENERGY`, `CHOPPY`면 감점
- `htf_bullish == false`면 큰 감점

권장 비중:

- `30%`

### 3. Execution Quality Score

최근 주문 품질이 나쁘면 좋은 신호라도 축소합니다.

입력 후보:

- `fill_quality_snapshot.avg_fill_ratio`
- `sample_count`
- 거래소별 `api_latency_ms` 최근 평균
- 슬리피지 또는 best bid/ask 품질

예시 해석:

- 최근 fill ratio 낮음 -> 감점
- 업비트 지연 큼 -> 감점
- OKX 상대적 안정 -> 중립 또는 소폭 가산

권장 비중:

- `20%`

### 4. Portfolio Diversification Score

이미 같은 성격의 노출이 많은지 반영합니다.

입력 후보:

- `correlation_with_btc`
- 현재 보유 자산의 집중도
- 동일 계열 자산 편중 여부

예시 해석:

- BTC와 지나치게 높은 상관 -> 감점
- 이미 해당 자산 cost basis 비중이 높음 -> 감점

권장 비중:

- `10%`

---

## 점수 계산 예시

예시 공식:

`allocation_score = 0.4 * signal_score + 0.3 * market_quality + 0.2 * execution_quality + 0.1 * diversification_quality`

그 다음 점수를 스케일로 바꿉니다.

예시:

- `score >= 85` -> `1.10`
- `75 <= score < 85` -> `1.00`
- `65 <= score < 75` -> `0.90`
- `55 <= score < 65` -> `0.75`
- `score < 55` -> `0.60`

이렇게 계단형으로 먼저 시작하는 것이 안전합니다.

이유:

- 연속 함수보다 해석이 쉽습니다.
- 로그에 바로 설명하기 쉽습니다.
- 튜닝 시 과민 반응이 줄어듭니다.

---

## 추천 시장 점수 규칙

### 알트

- `signal_score >= 70` 이면 기본 가점
- `volume_ratio >= min_volume_ratio * 1.2` 이면 추가 가점
- `htf_bullish == true` 이면 가점
- `symbol_regime in {TRENDING, BREAKOUT_ATTEMPT}` 이면 가점
- `LOW_ENERGY`, `CHOPPY`, `EXHAUSTION_RISK` 이면 감점
- `손절 후 패턴 재진입 차단 중`이면 큰 감점

### BTC

- `signal_score >= 72` 이면 기본 가점
- `confirm_bullish == true` 이면 큰 가점
- `fresh_cross == true` 이면 추가 가점
- `CHOPPY_HIGH_VOL`, `LOW_ENERGY` 이면 감점
- `confirm=false` 이면 큰 감점
- `손절 후 패턴 재진입 차단 중`이면 큰 감점

---

## 권장 구현 위치

### 1. 설정

- [settings/portfolio_allocator.py](/Users/plo/Documents/auto_coin_bot/settings/portfolio_allocator.py)

추가 후보:

- `enable_score_based_scaling`
- `score_scale_min`
- `score_scale_max`
- `signal_weight`
- `market_weight`
- `execution_weight`
- `diversification_weight`

### 2. 계산 helper

- [core/risk/allocation.py](/Users/plo/Documents/auto_coin_bot/core/risk/allocation.py)

추가 후보 함수:

- `compute_allocation_score(...)`
- `map_score_to_scale(...)`

### 3. 실제 호출 위치

- [ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/ma_crossover_bot.py)
- [upbit_ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_ma_crossover_bot.py)
- [okx_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/okx_btc_ema_trend_bot.py)
- [upbit_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_btc_ema_trend_bot.py)

기존 `base_position_ratio -> regime_scale -> btc_scale`
뒤에 `score_scale`을 마지막으로 곱하는 방식이 가장 안전합니다.

---

## 로그 설계

반드시 아래 항목을 같이 남겨야 합니다.

- `allocation_score`
- `allocation_score_scale`
- `allocation_signal_score`
- `allocation_market_score`
- `allocation_execution_score`
- `allocation_diversification_score`
- `allocation_reason_top`

예시:

- `signal strong + HTF bullish + volume strong`
- `blocked by low execution quality`
- `reduced by correlation penalty`

이렇게 남겨야 나중에

- 왜 이 비중이 나왔는지
- 왜 확대되지 않았는지
- 왜 특정 심볼만 계속 축소됐는지

를 바로 설명할 수 있습니다.

---

## 운영 원칙

이 구조는 반드시 아래 순서로 가는 것이 맞습니다.

1. `축소 먼저`
2. `확대는 좁게`
3. `계단형 스케일 먼저`
4. `로그 설명 가능성 유지`

즉

- 좋은 심볼을 무조건 크게 늘리는 시스템이 아니라
- 나쁜 심볼을 더 강하게 줄이고
- 정말 좋은 심볼만 조금 더 싣는 구조

가 이 프로젝트에 맞습니다.

---

## 권장 1차 값

보수형 시작값:

- `score_scale_min = 0.60`
- `score_scale_max = 1.10`
- `signal_weight = 0.40`
- `market_weight = 0.30`
- `execution_weight = 0.20`
- `diversification_weight = 0.10`

계단형:

- `>= 85` -> `1.10`
- `75 ~ 84.99` -> `1.00`
- `65 ~ 74.99` -> `0.90`
- `55 ~ 64.99` -> `0.75`
- `< 55` -> `0.60`

---

## 구현 순서

1. score 계산 helper 추가
2. 로그만 남기는 shadow mode
3. 실제 `score_scale` 적용
4. 백테스트/실거래 비교
5. 거래소별 가중치 분리 여부 판단

추천은 1, 2단계를 먼저 하고 실제 자금 반영은 그 다음입니다.

---

## 결론

score 기반 동적 자본 배분은 충분히 가치가 있습니다.

다만 이 프로젝트에서는

- `수익 확대`
보다
- `손실 구간 축소`

가 더 중요하므로,
`동적 확대 시스템`보다
`설명 가능한 동적 축소 + 제한적 확대 시스템`
으로 설계하는 것이 맞습니다.
