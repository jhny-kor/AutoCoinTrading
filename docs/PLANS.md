# PLANS

## 문서 사용 규칙

- `현재 적용`이라고 적힌 내용은 지금 코드와 `.env` 기준으로 맞춰 둡니다.
- `과거 검토안` 또는 `초기 이력`은 당시 비교/검토 메모로 남기며, 현재 값과 다를 수 있습니다.
- `향후 후보안`은 아직 적용하지 않은 아이디어입니다.
- 따라서 이 문서는 현재 운영 기준만 적는 문서가 아니라, 현재 상태와 검토 흐름을 함께 남기는 작업 메모로 봅니다.

## 현재 적용 전략

현재는 `단타/인트라데이 전용`으로 `BTC 전용 전략`과 `알트 전용 전략`을 나누어 운영합니다.

### 2026-05-07 현재 리팩토링 기준

- 운영 전략 동작은 유지하고, 네 개 실거래 봇에 흩어져 있던 신규 진입 비중 계산을 [core/risk/allocation.py](/Users/plo/Documents/auto_coin_bot/core/risk/allocation.py) 로 모았습니다.
- 알트 신규 진입 비중은 공통 helper 에서 아래 순서로 계산합니다.
  - `기본 비중`
  - `심볼 레짐 스케일`
  - `BTC 레짐 스케일`
  - `BTC ATR 스케일`
  - `ALT ATR 스케일`
  - `allocation score 스케일`
  - `volume spike / mean reversion / low energy probe 보정`
- BTC 신규 진입 비중은 공통 helper 에서 아래 순서로 계산합니다.
  - `기본 비중`
  - `BTC 심볼 레짐 스케일`
  - `BTC ATR 스케일`
  - `allocation score 스케일`
  - `low energy probe 보정`
- OKX/업비트 봇은 같은 결과 객체와 같은 로그 formatter 를 사용하므로, 이후 포지션 비중 관련 수정은 전략 본체보다 [core/risk/allocation.py](/Users/plo/Documents/auto_coin_bot/core/risk/allocation.py)를 먼저 봅니다.
- 이 리팩토링은 계산 위치만 바꾼 것이며, 설정값과 진입/청산 조건은 바꾸지 않았습니다.

### 2026-04-18 현재 적용 핵심 강화 요약

- 4차 진입 모드 전환
  - 알트: `Bollinger Squeeze + 거래량 폭발 돌파` 모드를 실제 운영 기본값으로 전환. `STRATEGY_ENTRY_MODE="squeeze"`.
  - BTC: `Donchian Channel + ATR 돌파` 모드를 실제 운영 기본값으로 전환. `BTC_TREND_ENTRY_MODE="donchian"`.
  - 해석:
    - BTC는 EMA 크로스 노이즈를 줄이고, 채널 돌파형 강추세만 더 선별적으로 추종합니다.
    - 알트는 단순 MA 돌파보다 `밴드 수축 + 거래량 확장` 구간만 우선 진입해 후속 탄력이 약한 진입을 줄입니다.

### 2026-04-06 현재 적용 핵심 강화 요약

- 3차 로직 강화 (병렬 진입 모드 추가)
  - 알트: `Bollinger Squeeze + 거래량 폭발 돌파` 진입 모드 추가. 기존 골든크로스 로직 의존성을 낮추고, 밴드 수축 및 거래량 폭발 동반 상단 돌파 시 즉각 진입. `STRATEGY_ENTRY_MODE="squeeze"` 로 변환 가능.
  - BTC: `Donchian Channel + ATR 돌파` 진입/청산 로직 통합. 잦은 EMA 크로스오버로 인한 노이즈를 방지하고, 최고/최저가 돌파 기반으로 강추세를 추종. `BTC_TREND_ENTRY_MODE="donchian"` 설정 지원.

### 2026-04-03 현재 적용 핵심 강화 요약

- 1차 강화
  - 알트: `RSI`, `MACD 히스토그램`, `MA/가격 기울기`, `신호 스코어` 기반 진입 품질 보강
  - BTC: `RSI`, `볼린저 밴드 폭`, `EMA 기울기`, `신호 스코어` 기반 진입 품질 보강
  - 노이즈 비율 평균을 이용해 알트는 `min_gap_pct`, BTC는 `EMA 스프레드/신호 스코어 기준`을 동적으로 보정
  - 레짐: `ADX(14)` 기반 `TRENDING/CHOPPY` 재분류와 레짐별 손절/익절/ATR/동적 오버웨이트 정책 분리
  - 청산: 알트 브레이크이븐 가드에 `MFE 대비 최대 이익 반납폭` 조건 추가
- 2차 강화
  - 진입 상태 머신 `WATCH -> ARM -> READY -> HOLD` 적용
  - 알트는 `BTC 상관관계 필터` 적용
  - BTC/알트 모두 `fill_ratio` 기반 실행 품질 가드 적용
  - 퍼널과 metrics 에 `signal_score`, `entry_timing_*`, `correlation_with_btc`, `fill_quality_*` 필드 추가
  - 알트는 `BTC 레짐`, `BTC ATR 퍼센트`를 추가로 읽어 신규 진입 비중을 단계형으로 축소
- 운영 해석
  - 약한 단발 신호는 즉시 진입하지 않고 누적 확인 후 진입
  - BTC와 과도하게 같은 방향으로 흔들리는 알트는 신규 진입 축소
  - 최근 체결 품질이 나쁜 심볼은 자동으로 잠시 쉬게 해 주문 품질 악화를 회피
  - 캔들 잡음이 많은 날은 진입 문턱을 자동으로 높이고, 추세가 깔끔한 날은 문턱을 자동으로 낮춤
  - BTC가 `LOW_ENERGY`이거나 `atr_pct`가 매우 낮은 구간에서는 알트 신규 진입을 바로 끄기보다 먼저 비중을 줄여 저엣지 진입을 완화

- BTC 전용 전략
  - 기본 개념: 5분봉 `Donchian + ATR` 추세추종 + 15분봉 확인
  - 매수 조건: Donchian 상단 돌파, 거래량, ATR, RSI, 볼린저 밴드 폭, EMA 기울기, 상위 타임프레임 조건을 만족하고 상태 머신 확인을 통과할 때
  - 청산 조건: ATR 또는 최근 스윙 기반 손절, Donchian 하단 이탈, 부분익절 후 잔량 트레일링, 수수료 반영 순익 보호 익절
  - 현재 적용 핵심값:
    - `BTC_TREND_MIN_EMA_SPREAD_PCT_MAP=BTC/USDT:0.030,BTC/KRW:0.030`
    - `BTC_TREND_SIGNAL_SCORE_MIN=62`
    - `BTC_TREND_ENTRY_CONFIRMATION_LOOPS=3`
    - `BTC_TREND_ENABLE_STOP_LOSS_PATTERN_REENTRY=true`
    - `BTC_TREND_STOP_LOSS_PATTERN_MIN_COOLDOWN_SEC=180`
    - `BTC_TREND_STOP_LOSS_PATTERN_MIN_SIGNAL_SCORE=72`
    - `BTC_TREND_STOP_LOSS_PATTERN_REQUIRE_CONFIRM_BULLISH=true`
    - `BTC_TREND_STOP_LOSS_PATTERN_REQUIRE_FRESH_CROSS=true`
    - `BTC_TREND_STOP_LOSS_PATTERN_RELAXED_FRESH_CROSS_AFTER_SEC_MAP=BTC/USDT:300,BTC/KRW:600`
    - `BTC_TREND_STOP_LOSS_PATTERN_RELAXED_FRESH_CROSS_MIN_SIGNAL_SCORE_MAP=BTC/USDT:85,BTC/KRW:90`
    - `BTC_TREND_MIN_VOLUME_RATIO_MAP=BTC/USDT:1.70,BTC/KRW:1.55`
    - `BTC_TREND_CHOPPY_MIN_VOLUME_RATIO_MAP=BTC/USDT:2.20,BTC/KRW:2.20`
    - `BTC_TREND_REGIME_POSITION_SCALE_MAP=TRENDING:1.10,BREAKOUT_ATTEMPT:0.90,CHOPPY:0.50,LOW_ENERGY:0.00,OVERHEATED:0.30,EXHAUSTION_RISK:0.00`
    - `BTC_TREND_STOP_LOSS_REENTRY_COOLDOWN_SEC=1200`
    - `BTC_TREND_PARTIAL_TAKE_PROFIT_RATIO=0.4`
    - `BTC_TREND_TAKE_PROFIT_ATR_MULTIPLE=1.8`
    - `BTC_TREND_TRAILING_DRAWDOWN_PCT=0.6`
    - `BTC_TREND_ATR_POSITION_SCALE_THRESHOLD_MAP=0.16:0.80,0.13:0.60,0.10:0.35`
  - 현재 해석:
    - `BTC/USDT`, `BTC/KRW` 모두 최근 손실 거래의 `MFE` 가 매우 낮아, 진입 횟수보다 진입 질을 더 우선하도록 조정
    - `CHOPPY` 구간은 신규 진입 자체를 더 보수적으로 막고, 상태 머신 확인 횟수도 늘려 약한 추세 유지 진입을 줄임
    - 손절 후 재진입도 이제는 `시간 경과만`이 아니라 `confirm + fresh cross + 점수 복구`가 함께 보여야 허용
    - 다만 BTC는 `confirm=true`와 높은 점수가 충분히 유지되면 일정 시간 뒤 `fresh_cross` 없이도 예외 재진입이 가능하도록 완화
    - BTC도 `regime`뿐 아니라 `ATR 퍼센트`가 너무 낮은 구간에서는 신규 진입 비중을 단계형으로 줄여 저변동 구간 과진입을 완화
- 알트 전용 전략
  - 기본 개념: 1분봉 `Bollinger Squeeze + 거래량 확장` 기반 돌파 추종
  - 매수 조건: 밴드폭이 기준 이하로 수축한 뒤 상단 돌파가 나오고, 거래량 확장, RSI, MACD, 기울기, 상태 머신 조건을 함께 통과할 때
  - 일반 매도 조건: 가격이 이동평균선을 위에서 아래로 이탈하고, 최소 익절률 또는 순익 보호 익절 조건을 만족할 때
  - 손절 조건: 손실률이 코인별 기준보다 커지면 데드크로스 없이 즉시 전량 청산
  - 분할 진입: 한 번에 전량 진입하지 않고 설정된 비율만큼 나눠서 진입
  - 분할 청산: 익절 시에는 나눠서 청산하고, 손절 시에는 전량 청산
  - 추가 매수 제한: 평균 진입가보다 설정된 비율 이상 더 낮아졌을 때만 추가 매수
  - 공통 필터: 쿨다운, 최소 이격도, RSI, MACD, 상위 타임프레임, 거래량, 변동성, BTC 상관관계, 체결 품질, 일일 최대 손실 제한, 목표 비중 기반 신규 매수 제한
  - 코인별 설정 분리: 이격도, 익절률, 손절률, 최소 주문 수량을 코인별로 다르게 적용
  - 현재 적용 핵심값:
    - `STRATEGY_ENABLE_STOP_LOSS_PATTERN_REENTRY=true`
    - `STRATEGY_STOP_LOSS_PATTERN_MIN_COOLDOWN_SEC=180`
    - `STRATEGY_STOP_LOSS_PATTERN_MIN_SIGNAL_SCORE=70`
    - `STRATEGY_STOP_LOSS_PATTERN_MIN_VOLUME_RATIO_MULTIPLIER=1.20`
    - `STRATEGY_STOP_LOSS_PATTERN_REQUIRE_HTF_BULLISH=true`
    - `STRATEGY_STOP_LOSS_PATTERN_REQUIRE_FRESH_CROSS=true`
    - `ETH/USDT` 최소 거래량 배수 `0.80`
    - `ETH/KRW` 최소 거래량 배수 `1.20`
    - `ETH/KRW` 포지션 비중 `0.45`
    - `ETH/KRW` 최소 이격도 `0.15`
    - `XRP/KRW` 최소 익절률 `0.40`
    - `XRP/USDT` 최소 익절률 `0.55`
    - `XRP/KRW` 순익 보호 최소 순익률 `0.10`
    - `XRP/USDT` 순익 보호 최소 순익률 `0.10`
    - `XRP/KRW`, `XRP/USDT` 브레이크이븐 가드 최소 MFE `0.15`
    - `XRP/KRW`, `XRP/USDT` 브레이크이븐 가드 순익 바닥 `0.12`
    - `STRATEGY_REGIME_POSITION_SCALE_MAP=TRENDING:1.00,BREAKOUT_ATTEMPT:0.80,CHOPPY:0.40,LOW_ENERGY:0.00,OVERHEATED:0.20,EXHAUSTION_RISK:0.00`
    - `STRATEGY_BTC_REGIME_POSITION_SCALE_MAP=LOW_ENERGY:0.50`
    - `STRATEGY_BTC_REGIME_POSITION_SCALE_OVERRIDE_MAP=ETH/KRW|LOW_ENERGY:0.35,XRP/KRW|LOW_ENERGY:0.60,ETH/USDT|LOW_ENERGY:0.35,XRP/USDT|LOW_ENERGY:0.60`
    - `STRATEGY_BTC_ATR_POSITION_SCALE_THRESHOLD_MAP=0.18:0.70,0.15:0.45,0.12:0.25`
    - `STRATEGY_BLOCK_ENTRY_WHEN_HTF_BEARISH_SYMBOLS=XRP/KRW,ETH/USDT,ETH/KRW`
    - `ANALYSIS_OKX_SYMBOLS=SOL/USDT`
    - `ANALYSIS_UPBIT_SYMBOLS=SOL/KRW`
  - 현재 해석:
    - `ETH/KRW` 는 최근 손실이 반복돼 청산보다 진입 자체를 줄이는 쪽으로 더 보수화
    - `XRP/KRW`, `XRP/USDT` 는 작은 수익 후 큰 손실 한두 건이 손익을 무너뜨려 보호 장치를 더 빨리 켜도록 조정
    - XRP 계열은 `break_even_guard_take_profit` 이 실제로 음수로 끝난 사례가 있어, 이제는 더 이른 MFE 와 더 높은 순익 바닥을 요구하도록 보강
    - 손절 후 재진입도 `최소 180초 + 더 높은 신호 점수 + 강화된 거래량 + HTF 상승 + fresh cross`가 같이 확인될 때만 허용
    - 2026-04-09 오전 로그 기준으로는 대부분 `HTF 하락` 또는 `fresh cross 부재` 때문에 막혀 있어, 현재 강도는 과도하기보다 회복 전 재진입 억제용에 가까움
    - 레짐별 포지션 비중 1차 적용으로 상승장/횡보장/저에너지장에 따라 진입 크기도 다르게 조절
    - 최근 3일 업비트 실거래 기준으로는 `BTC LOW_ENERGY`, `낮은 BTC atr_pct` 구간에서 알트 손실 캠페인이 상대적으로 많아, 알트 자체 레짐 외에 `BTC 상태 기반 축소`를 추가 적용
    - `SOL`은 우선 분석 수집만 추가하고, 최근 `volume_ratio`, `avg_abs_change_pct`, `ready 빈도`, `실제 최소 주문 금액 적합성`이 충분히 쌓이면 실거래 후보로 올림

장타/스윙 전용 구조와 초기 전략안은 별도 폴더 `/Users/plo/Documents/auto_coin_bot_swing` 에 정리합니다.

## 현재 적용 운영 안정화 보완

- 업비트 공용 API 호출에는 `429 Too Many Requests` 완화를 위한 짧은 backoff 재시도가 들어가 있습니다.
- 업비트 시장가 매수는 가용 KRW를 전부 쓰지 않도록 주문 버퍼를 둡니다.
- 목적은 `insufficient_funds_bid` 와 연속 주문 실패를 줄이는 것입니다.
- `ETH/KRW` 는 심볼별 거래량, 최소 이격도, 브레이크이븐 가드 기준을 더 보수적으로 조정해 약한 진입과 작은 수익 반납을 줄입니다.
- 업비트는 최근 실행 품질 로그에서 `api_latency_ms` 가 `약 1초` 수준이라, 현재는 아래 완화책을 적용했습니다.
  - 잔고 조회 짧은 캐시 `UPBIT_BALANCE_CACHE_TTL_SEC=1.0`
  - 호가 조회 짧은 캐시 `UPBIT_ORDERBOOK_CACHE_TTL_SEC=0.8`
  - 최소 주문 경계 근처에서만 best bid 재조회 `UPBIT_BEST_BID_REFRESH_BUFFER_PCT=0.30`
  - 시장가 매도도 공통 재시도 경로 사용
  - 주문 직후 잔고/호가 캐시 무효화

## 현재 적용 포트폴리오 배분

- 기준 목표 비중
  - BTC `60%`
  - ETH `30%`
  - XRP `10%`
- 1차 적용 방식
  - 강제 리밸런싱 매도는 하지 않음
  - 신규 매수만 제한
  - 총 지갑 금액은 `가용 현금 + 남아 있는 누적 투입 원가` 기준으로 계산
  - 코인별 누적 투입 원가는 체결 로그 기준으로 매수 누적 후, 매도 비율만큼 차감하는 방식으로 관리
- 2차 확장
  - 거래량과 추세 품질이 강한 코인만 목표 비중을 일시적으로 `+5%` 확대
  - 보수형 시작을 원칙으로 함
- 3차 확장
  - score 기반 동적 배분 적용
  - 최종 비중은 `기본 비중 x 레짐/ATR 스케일 x score_scale`
  - score 축
    - `signal`
    - `market`
    - `execution`
    - `diversification`
  - 현재 score 스케일 버킷
    - `>=85 -> 1.10`
    - `>=75 -> 1.00`
    - `>=65 -> 0.90`
    - `>=55 -> 0.75`
    - `<55 -> 0.60`
  - 현재 해석
    - 최근 로그에서는 확대보다 축소가 더 자주 작동하고 있음
    - 즉 현재 구조는 “좋은 심볼 적극 확대”보다 “질 낮은 심볼 자동 축소”에 더 초점을 둔 보수형 배분으로 이해하는 편이 맞음
    - `allocation_reason_top` 도 이제 최고 점수 축이 아니라 최저 점수 축 기준이라 실제 약점 설명에 더 가깝게 읽힘

## 현재 적용 운영 복구 흐름

- 에러 발생 시 텔레그램 인시던트 메시지를 전송합니다.
- 현재 버튼 승인형 1차 구현 범위
  - `재기동`
  - `상세 보기`
  - `수정 요청`
  - `무시`
- 현재 자동화 수준
  - `재기동`은 실제로 봇 stop/start 까지 수행
  - `수정 요청`은 인시던트를 기록하고 텔레그램으로 접수 메시지를 다시 보냄
  - 실제 코드 패치와 git 커밋/푸시는 아직 수동 승인형 작업으로 유지

## 현재 로그에서 읽히는 특징

- 최근 이틀 실거래를 보면 `2026-03-31` 은 손절이 많아 약했고, `2026-04-01` 은 승률과 평균 순손익률이 모두 양호했습니다.
- 핵심 문제는 `손절폭 자체` 보다 `후속 탄력이 거의 없는 약한 진입` 이었습니다.
- 반대로 `BTC/USDT`, `XRP/KRW`, `XRP/USDT` 는 수익 거래가 나오는데도 `profit_protect` 와 `break_even` 이 빨라 `MFE` 대비 실현 순익이 작은 구간이 확인됐습니다.
- 업비트는 최근 실행 품질 기준 `api_latency_ms ≈ 1.0초`, `exchange_ack_latency_ms ≈ 0.55초` 수준이라 저엣지 진입에서는 불리합니다.
- OKX 는 최근 실행 품질 기준 `api_latency_ms ≈ 60ms` 수준이라 업비트보다 구조적으로 유리합니다.
- 따라서 현재 단계의 핵심은
  - `ETH/USDT`, `ETH/KRW`, `BTC/KRW` 의 약한 진입 손절을 줄이는 것
  - `BTC/USDT`, `XRP/KRW`, `XRP/USDT` 의 수익 러너를 조금 더 가져가는 것
  - 업비트 중복 REST 조회를 줄여 지연과 429 리스크를 낮추는 것
  - 저품질 체결 구간에서는 자동으로 쉬고, 상관도가 높은 알트 동시 진입을 줄이는 것
  입니다.

## 현재 로그 구조

- 운영용 텍스트 로그는 `logs/YYYY-MM-DD/*.log` 에 저장합니다.
- 장애 분석용 구조화 로그는 `structured_logs/live/YYYY-MM-DD/<program>/system.jsonl` 에 저장합니다.
- 전략 판단 로그는 `structured_logs/live/YYYY-MM-DD/<program>/strategy.jsonl` 에 저장합니다.
- 체결 결과는 `trade_logs/YYYY-MM-DD/trade_history.jsonl` 과 `structured_logs/live/YYYY-MM-DD/<program>/trade.jsonl` 에 함께 저장합니다.
- 퍼널 요약은 `structured_logs/live/YYYY-MM-DD/<program>/summary_1h/*.json` 에 시간 버킷별로 저장합니다.
- 최근 7일 로그는 원본을 유지하고, 그 이전은 날짜별 `tar.gz` 로 압축합니다.

현재부터는 로그를 눈으로 읽기보다 아래 관점으로 집계하는 것이 우선입니다.

- 단계별 통과율
- 차단 사유 비율
- buy_ready 대비 실제 filled 비율
- 진입 조건값과 손익의 관계
- 시간대별 또는 시간 버킷별 성과

## 로그를 보는 관점

- 첫 번째 관점: `수익`보다 `거래가 왜 막혔는지`를 먼저 봅니다.
  지금은 체결 표본이 적기 때문에, 손익보다 스킵 사유 분포가 더 중요한 지표입니다.
- 두 번째 관점: `코인별 성격 차이`를 분리해서 봅니다.
  BTC는 저변동 추세 확인형, PI/XRP는 상대적 고변동 대응형으로 나눠 생각하는 편이 좋습니다.
- 세 번째 관점: `신호 빈도`보다 `필터 통과율`을 봅니다.
  신호는 있어도 필터를 거의 못 통과하면, 전략은 사실상 진입 불가 상태일 수 있습니다.
- 네 번째 관점: `거래 횟수 증가`를 바로 목표로 두지 않습니다.
  저시드 테스트 단계에서는 과매매를 막는 것이 더 중요하고, 먼저 안전한 거래가 가능한지 확인해야 합니다.
- 다섯 번째 관점: `한 번의 체결 결과`보다 `누적 패턴`을 봅니다.
  최소 며칠 이상 쌓인 뒤에야 필터 조정이 의미 있고, 하루 단위 결과만 보고 성급히 바꾸지 않는 것이 좋습니다.

## BTC 체크포인트

- BTC는 현재 1분봉 기준으로 `저변동` 자산으로 해석합니다.
- 평균 이격도와 평균 절대 변화율이 모두 낮기 때문에, `신호 자체가 약한지`를 먼저 봅니다.
- `공개 기준 매수 준비 비율`이 0%에 가깝다면, 전략이 너무 보수적인 상태일 수 있습니다.
- 특히 `이격도 기준`, `최소 변동성 기준`, `거래량 배수 기준` 중 무엇이 가장 많이 막는지 봅니다.
- BTC는 거래가 적다고 바로 나쁘게 보지 말고, `수수료를 이길 만큼 움직일 수 있는지`를 먼저 봅니다.

BTC를 볼 때 핵심 질문

- 현재 이격도 기준이 너무 높은가
- 현재 변동성 기준이 BTC의 평균 움직임보다 높은가
- 거래량 배수 기준이 1분봉 BTC에는 너무 엄격한가
- 5분봉 상위 추세 필터가 너무 자주 역방향으로 막는가
- 실제로 거래가 늘어나더라도 수익보다 수수료가 더 커지지 않는가

## 알트 체크포인트

- PI/XRP는 BTC보다 `고변동` 자산으로 해석합니다.
- 신호가 잘 나오는지보다, `가짜 신호를 얼마나 잘 거르고 있는지`가 더 중요합니다.
- 상위 타임프레임 불일치, 거래량 부족, 추가 매수 조건 미충족이 핵심 차단인지 봅니다.
- 알트는 거래를 늘리는 것보다, 급등 추격과 급락 손절을 얼마나 안정적으로 관리하는지가 더 중요합니다.
- 체결이 생기면 승률보다 먼저 `익절 대비 손절 크기`, `보유 시간`, `재진입 빈도`를 봅니다.

알트를 볼 때 핵심 질문

- 상위 타임프레임과 반대로 진입하려는 경우가 많은가
- 거래량이 붙은 돌파만 골라내고 있는가
- 손절 없이 오래 물리는 구조는 아닌가
- 같은 코인을 너무 자주 재진입하고 있지는 않은가

## 현재 설정 방향

- 낮은 시드머니 테스트를 우선합니다.
- 진입 빈도보다 불필요한 거래를 줄이는 쪽에 무게를 둡니다.
- 업비트는 수수료 0.05%를 반영해 최소 익절 조건을 보수적으로 봅니다.
- OKX와 업비트는 같은 전략을 공유하지만 최소 주문 금액과 일일 손실 한도는 거래소별로 다르게 관리합니다.
- BTC처럼 잔잔한 코인과 PI처럼 변동성 큰 코인을 같은 값으로 보지 않고 코인별 설정을 사용합니다.

## 앞으로 1차 로드맵

### 1단계. 지금 반영한 보수화/익절 완화 관찰

- 최소 `1~3일` 은 현재 조정값 그대로 운용합니다.
- 확인할 핵심 항목
  - `ETH/USDT`, `ETH/KRW`, `BTC/KRW` 손절 건수 감소 여부
  - `BTC/USDT`, `XRP/KRW`, `XRP/USDT` 의 평균 순손익률과 `MFE 대비 실현 비율` 개선 여부
  - 업비트 `api_latency_ms`, `exchange_ack_latency_ms`, `fill_ratio` 변화 여부

### 2단계. 손절 방지 성과 점검

- `analyze_strategy_logs.py` 와 `trade_history.jsonl` 기준으로 최근 `3일` 손절만 따로 봅니다.
- 손절 건마다
  - 진입 직후 `MFE`
  - 상위 타임프레임 하락 여부
  - 거래량 부족 / 약한 스프레드 여부
  - 보유시간
  를 함께 비교합니다.
- 여기서도 `MFE < 0.15%` 수준의 약한 실패 진입이 반복되면 진입 필터를 한 단계 더 보수화합니다.

### 3단계. 수익 러너 확대 점검

- `BTC/USDT`, `XRP/KRW`, `XRP/USDT` 만 따로 묶어
  - 평균 `MFE`
  - 평균 실현 순익률
  - `실현 순익률 / MFE`
  를 비교합니다.
- 이 값이 여전히 `0.4` 아래에 머물면
  - BTC 는 트레일링 여유를 한 단계 더 넓힐지
  - XRP 는 순익 보호 최소 순익률을 더 올릴지
  검토합니다.

### 4단계. 업비트 지연 완화 2차 검토

- 현재는 짧은 TTL 캐시와 재시도 공통화만 적용했습니다.
- 다음 후보는
  - 잔고 조회를 루프 단위 1회로 더 줄이기
  - 호가 조회를 websocket 기반으로 대체하기
  - 주문 전/후 조회를 역할별로 더 분리하기
  입니다.
- 이 단계는 현재 캐시 적용 후에도 `api_latency_ms` 나 429 빈도가 체감상 크게 안 줄 때 진행합니다.
- 상세 설계안은 [docs/UPBIT_WEBSOCKET_TRANSITION_PLAN.md](/Users/plo/Documents/auto_coin_bot/docs/UPBIT_WEBSOCKET_TRANSITION_PLAN.md)에 따로 정리합니다.

### 5단계. 레짐별 포지션 비중 2차 설계

- 1차는 레짐별 `포지션 크기만` 조절합니다.
- 2차는 아래 확장을 검토합니다.
  - `TRENDING`에서 부분익절 비율 축소
  - `CHOPPY`에서 추가매수 비활성화
  - `LOW_ENERGY`에서 신규 진입 0 유지 + 보유 포지션만 관리
  - `BREAKOUT_ATTEMPT`에서 fresh cross 요구 강화
  - `OVERHEATED`에서 포지션 0.1~0.2x 유지 + 익절 빠르게
- 2차 설계 목표
  - 레짐별 진입 크기뿐 아니라 `익절/손절/추가매수 정책`도 분리
  - 동일 레짐이어도 `BTC`와 `알트`를 다르게 처리
  - 필요 시 심볼별 레짐 스케일 override 도입

2차 설계 후보 예시:

| 구분 | 1차 현재값 | 2차 후보 |
| --- | --- | --- |
| 알트 `TRENDING` | `1.00x` | `1.00x` 유지 + 부분익절 비율 축소 |
| 알트 `BREAKOUT_ATTEMPT` | `0.80x` | `0.70x` + fresh signal 요구 강화 |
| 알트 `CHOPPY` | `0.40x` | `0.25x` + 추가매수 비활성화 |
| BTC `TRENDING` | `1.10x` | `1.10x` 유지 + 러너 보유 우대 |
| BTC `BREAKOUT_ATTEMPT` | `0.90x` | `0.80x` + 진입 확인 루프 강화 |
| BTC `CHOPPY` | `0.50x` | `0.30x` + trend_follow 축소 |

## BTC가 초기에 잘 안 거래되던 이유 (과거 메모, 날짜 미기록)

- BTC/USDT 평균 이격도는 약 `0.07%`, BTC/KRW 평균 이격도는 약 `0.08%` 수준이라 당시 BTC 전용 기준 `0.15%`보다 작을 때가 많았습니다.
- BTC 계열 평균 절대 변화율은 약 `0.02% ~ 0.03%` 수준인데, 당시 최소 변동성 기준은 `0.05%`라서 변동성 필터에 자주 막힐 수 있었습니다.
- BTC 계열 평균 거래량 배수도 `0.4 ~ 0.5배` 수준이라 당시 최소 거래량 배수 `1.2배`를 넘기기 어려웠습니다.
- 상위 타임프레임 필터까지 켜져 있어서, 약한 1분봉 신호는 5분봉 추세와 안 맞는 경우 더 쉽게 보류됐습니다.
- 즉 이 시기의 BTC는 `시장 자체가 조용한데 필터는 상대적으로 강한 상태`라서 거래가 드문 구조였습니다.

BTC를 더 활발하게 보려면 나중에 검토할 항목

- BTC 전용 이격도 기준을 조금 더 낮출지
- BTC 전용 최소 변동성 기준을 더 낮출지
- BTC 전용 최소 거래량 배수를 완화할지
- 1분봉 매수에 대해 상위 타임프레임 필터를 다르게 적용할지
- 그래도 거래가 안 나오면 BTC는 더 긴 주기 전략으로 보는 것이 맞는지

### 4단계. 체결 성과 검증

- 체결 수
- 승률
- 평균 손익률
- 평균 보유 시간
- 손절 대비 익절 비율
- 거래소별 수수료 반영 후 순손익

### 5단계. 다음 전략 후보 검토

- RSI 필터
- 시간대 필터
- 하루 최대 거래 횟수 제한
- 일일 최대 수익 도달 시 거래 중단
- 코인별 거래량/변동성 기준 세분화

## 다음 로드맵

### 1단계. Donchian / Squeeze 검증

- 최소 `1~3일`은 현재 모드를 그대로 유지합니다.
- 확인 항목
  - BTC: 거래 수, `stop_loss` 비중, 평균 `MFE`, 평균 순손익률
  - 알트: 진입 수 감소 여부, `profit_protect` / `break_even_guard` 비중 증가 여부
  - 공통: `buy_ready -> filled` 비율, 심볼별 진입 차단 이유 분포

### 2단계. BTC Donchian 세부 튜닝

- 우선 조정 후보
  - `BTC_TREND_DONCHIAN_ENTRY_LOOKBACK`
  - `BTC_TREND_DONCHIAN_EXIT_LOOKBACK`
  - `BTC_TREND_DONCHIAN_CONFIRM_BREAKOUT_CLOSE`
- 목표
  - 약한 돌파 추격은 줄이고
  - `partial_take_profit -> trailing_take_profit` 러너 비중을 늘립니다.

### 3단계. 알트 Squeeze 세부 튜닝

- 우선 조정 후보
  - `STRATEGY_SQUEEZE_MAX_BANDWIDTH_PCT`
  - `STRATEGY_SQUEEZE_MIN_VOLUME_RATIO`
  - 심볼별 `min_volume_ratio`, `max_entry_gap_pct`
- 목표
  - 후속 탄력 없는 진입 감소
  - `ETH/USDT`, `ETH/KRW`, `XRP/KRW`, `XRP/USDT` 중 실제로 squeeze가 잘 맞는 심볼 선별

### 4단계. 잔량 러너 관리 분리

- 다음 후보는 새 진입보다 `부분익절 후 잔량 전용 관리` 입니다.
- 목표
  - BTC/XRP의 러너를 더 길게 가져가고
  - 이미 잠근 수익을 다시 크게 반납하지 않도록 분리 관리합니다.

### 5단계. 레짐 전환형 전략 선택기

- Donchian / Squeeze 검증이 끝나면
  - `TRENDING`에서만 적극 진입
  - `CHOPPY`, `LOW_ENERGY`에서는 더 보수적인 경로
로 확장합니다.
- 목표
  - 전략 자체보다 장세별 적용 전략을 다르게 해 손절과 과매매를 더 줄이는 것입니다.

### 6단계. 그 이후 후보

- `KAMA 적응형 평균`
  - 우선 `ETH/USDT`, `ETH/KRW` 실험용 후보
- `Cross-Sectional Momentum 로테이션`
  - 당장 매매 규칙보다 `후보 심볼 리포트`를 먼저 만드는 쪽이 맞습니다.
- 판단 기준
  - 현재 Donchian / Squeeze가 기대만큼 개선되지 않을 때만 2차 전략으로 진행합니다.

## 향후 후보안

### 미래 전략 후보 비교표

| 후보 | 핵심 아이디어 | 기대 효과 | 현재 구조 적합도 | 구현 난이도 | 우선순위 |
| --- | --- | --- | --- | --- | --- |
| BTC Donchian + ATR 돌파 | `n봉 최고가 돌파 진입 + ATR 손절 + 채널 이탈 청산` | 약한 EMA 크로스 노이즈 축소, 추세 러너 확대 | 높음 | 중간 | 1 |
| 알트 Bollinger Squeeze 돌파 | 변동성 압축 후 상단 돌파 + 거래량 확장 진입 | 후속 탄력 없는 약한 알트 진입 감소 | 높음 | 중간 | 2 |
| 레짐 전환형 전략 선택기 | `TRENDING`이면 추세추종, `CHOPPY/LOW_ENERGY`면 진입 중단 또는 다른 규칙 사용 | 장세에 따라 전략을 다르게 써 손절과 과매매 감소 | 높음 | 중간~높음 | 3 |
| 알트 Cross-Sectional Momentum 로테이션 | 최근 강한 코인 상위 몇 개만 거래 | 상대강도 높은 심볼에 집중 | 중간 | 높음 | 4 |
| KAMA 적응형 평균 전략 | 고정 MA 대신 적응형 평균으로 노이즈 완화 | ETH 같은 애매한 구간 가짜 돌파 감소 | 중간 | 중간 | 5 |
| 부분익절 후 잔량 전용 관리 | 부분익절 후 잔량은 별도 트레일링/순익보호 규칙 사용 | BTC/XRP 러너 확대 | 높음 | 낮음~중간 | 6 |

### 미래 전략 설계 메모

- 참고 방향
  - 추세추종: Turtle/Donchian, Time Series Momentum 계열
  - 적응형 평균: Perry Kaufman 계열
  - 변동성 압축 돌파: Bollinger Squeeze 계열
  - 상대강도 로테이션: Cross-sectional Momentum 계열
- 현재 코드 기준으로는 `새 지표를 추가해 기존 엔진에 얹는 방식`이 가장 안전합니다.
- 따라서 완전히 별도 프로젝트를 늘리기보다, 먼저 `core/strategy`, `core/risk`, `settings/` 확장으로 붙일 수 있는 후보부터 검토합니다.

### 장타/스윙 전용 분리 폴더 구축 (2026-03-21 기준 후보안)

- 방향
  - 기존 `auto_coin_bot` 는 단타/인트라데이 전용 유지
  - 장타는 새 폴더 `auto_coin_bot_swing` 으로 완전히 분리
- 이유
  - `.env`, 로그, 텔레그램 알림, 자동시작, 포트폴리오 배분이 단타와 장타에서 서로 섞이지 않도록 하기 위함
  - 장타는 `1h / 4h / 1d` 기반의 더 긴 보유 전략이 필요해 현재 1분봉/5분봉 구조와 성격이 다름
- 공통 모듈 재사용 후보
  - `bot_logger.py`
  - `telegram_notifier.py`
  - `telegram_command_listener.py`
  - `structured_log_manager.py`
  - `trade_history_logger.py`
  - `portfolio_allocator.py`
  - `log_path_utils.py`
- 초기 전략 방향
  - `BTC / ETH / XRP`
  - `1시간봉 진입 + 4시간봉 확인 + 일봉 레짐`
  - 손절 우선, 브레이크이븐 가드, 부분 익절, 트레일링 순서
  - 자세한 초안은 `SWING_BOT_DESIGN.md` 참고

## 앞으로 가능한 전략 개선

### 0. 후보별 구조 기준 설계안

#### A. BTC Donchian + ATR 돌파

- 적용 대상
  - `BTC/USDT`
  - `BTC/KRW`
- 새 설정 후보
  - `BTC_TREND_ENTRY_MODE=ema|donchian`
  - `BTC_TREND_DONCHIAN_ENTRY_LOOKBACK=20`
  - `BTC_TREND_DONCHIAN_EXIT_LOOKBACK=10`
  - `BTC_TREND_DONCHIAN_CONFIRM_BREAKOUT_CLOSE=true`
- 코드 시작점
  - [settings/btc_trend_settings.py](/Users/plo/Documents/auto_coin_bot/settings/btc_trend_settings.py)
  - [core/strategy/btc.py](/Users/plo/Documents/auto_coin_bot/core/strategy/btc.py)
  - [upbit_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_btc_ema_trend_bot.py)
  - [okx_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/okx_btc_ema_trend_bot.py)
- 설계 포인트
  - 현재 EMA 진입과 병렬 실험이 가능하도록 `entry_mode` 를 두는 편이 안전합니다.
  - 청산은 기존 ATR/트레일링/부분익절 구조를 최대한 재사용합니다.

#### B. 알트 Bollinger Squeeze 돌파

- 적용 대상
  - 우선 `ETH/USDT`, `ETH/KRW`, `XRP/KRW`, `XRP/USDT`
- 새 설정 후보
  - `STRATEGY_ENTRY_MODE=ma|squeeze`
  - `STRATEGY_BB_PERIOD=20`
  - `STRATEGY_BB_STDDEV=2.0`
  - `STRATEGY_SQUEEZE_MAX_BANDWIDTH_PCT=...`
  - `STRATEGY_SQUEEZE_MIN_VOLUME_RATIO=...`
- 코드 시작점
  - [settings/strategy_settings.py](/Users/plo/Documents/auto_coin_bot/settings/strategy_settings.py)
  - [core/strategy/alt.py](/Users/plo/Documents/auto_coin_bot/core/strategy/alt.py)
  - [upbit_ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_ma_crossover_bot.py)
  - [ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/ma_crossover_bot.py)
- 설계 포인트
  - 기존 MA 돌파 전략을 없애지 말고, `entry_mode` 로 병렬 실험하는 게 좋습니다.
  - 최근 손절 원인이 약한 후속 탄력이라, 밴드폭 축소 여부를 진입 전 필수 조건으로 두는 방향이 맞습니다.

#### C. 레짐 전환형 전략 선택기

- 적용 대상
  - 전 심볼 공통
- 새 설정 후보
  - `STRATEGY_ENABLE_REGIME_STRATEGY_SWITCH=true`
  - `STRATEGY_TRENDING_ENTRY_MODE=...`
  - `STRATEGY_CHOPPY_ENTRY_MODE=disabled|mean_reversion`
  - `BTC_TREND_CHOPPY_ENTRY_MODE=disabled|conservative`
- 코드 시작점
  - [settings/market_regime_guard.py](/Users/plo/Documents/auto_coin_bot/settings/market_regime_guard.py)
  - [core/strategy/alt.py](/Users/plo/Documents/auto_coin_bot/core/strategy/alt.py)
  - [core/strategy/btc.py](/Users/plo/Documents/auto_coin_bot/core/strategy/btc.py)
- 설계 포인트
  - 지금은 레짐이 `진입 차단` 용도에 가깝습니다.
  - 다음 단계는 레짐을 `전략 선택` 용도로 승격하는 것입니다.

#### D. 알트 Cross-Sectional Momentum 로테이션

- 적용 대상
  - 분석 수집 심볼 전체
- 새 설정 후보
  - `ROTATION_ENABLE=true`
  - `ROTATION_LOOKBACK_DAYS=7`
  - `ROTATION_TOP_N=3`
  - `ROTATION_MIN_LIQUIDITY_THRESHOLD=...`
- 코드 시작점
  - [analysis_log_collector.py](/Users/plo/Documents/auto_coin_bot/analysis_log_collector.py)
  - [tools/discover_untracked_symbols.py](/Users/plo/Documents/auto_coin_bot/tools/discover_untracked_symbols.py)
  - [portfolio_allocator.py](/Users/plo/Documents/auto_coin_bot/portfolio_allocator.py)
- 설계 포인트
  - 이 후보는 전략 계산보다 `심볼 선택` 레이어가 먼저 필요합니다.
  - 따라서 당장 매수 규칙보다도 `후보 심볼 선정 리포트` 를 먼저 만드는 편이 낫습니다.

#### E. KAMA 적응형 평균 전략

- 적용 대상
  - 우선 `ETH/USDT`, `ETH/KRW`
- 새 설정 후보
  - `STRATEGY_MA_TYPE=sma|kama`
  - `STRATEGY_KAMA_ER_PERIOD=10`
  - `STRATEGY_KAMA_FAST=2`
  - `STRATEGY_KAMA_SLOW=30`
- 코드 시작점
  - [core/strategy/alt.py](/Users/plo/Documents/auto_coin_bot/core/strategy/alt.py)
  - [settings/strategy_settings.py](/Users/plo/Documents/auto_coin_bot/settings/strategy_settings.py)
- 설계 포인트
  - ETH는 최근 손절 억제가 우선이라, 고정 SMA보다 적응형 평균이 가짜 돌파를 줄일 수 있는지 실험 가치가 있습니다.
  - 이 전략은 범용 도입보다 `ETH 전용 실험`으로 시작하는 편이 안전합니다.

#### F. 부분익절 후 잔량 전용 관리

- 적용 대상
  - `BTC/USDT`, `BTC/KRW`, `XRP/KRW`, `XRP/USDT`
- 새 설정 후보
  - `BTC_TREND_DISABLE_TREND_EXIT_AFTER_PARTIAL_TP=true`
  - `BTC_TREND_RUNNER_MIN_PROFIT_PROTECT_PCT=...`
  - `STRATEGY_RUNNER_MODE_SYMBOLS=...`
- 코드 시작점
  - [core/strategy/btc_position.py](/Users/plo/Documents/auto_coin_bot/core/strategy/btc_position.py)
  - [core/strategy/btc.py](/Users/plo/Documents/auto_coin_bot/core/strategy/btc.py)
  - [core/risk/alt_exit.py](/Users/plo/Documents/auto_coin_bot/core/risk/alt_exit.py)
- 설계 포인트
  - 현재 구조를 가장 적게 흔드는 후보입니다.
  - 로그 기준으로 러너가 있는데 너무 일찍 잠그는 문제를 해결하는 데 직접적입니다.

### BTC 별도 실험 전략

- 별도 실험 파일
  - `okx_btc_ema_trend_bot.py`
  - `upbit_btc_ema_trend_bot.py`
  - 메인 개념
  - 5분봉 또는 15분봉 EMA 추세추종
  - 거래량 확인 유지
  - 변동성 필터는 ATR 비율 기준
  - 현재는 보수적 1회 추가매수 허용
  - 손절은 ATR 또는 최근 스윙 기준
  - 익절은 목표 구간 도달 후 전량 트레일링 청산 + 수수료 반영 순익 보호 익절
- 주의
  - 기존 BTC 포함 봇과 동시에 실행하면 같은 BTC 심볼을 중복 매매할 수 있으므로 함께 실행하지 않는 것이 안전합니다.

### BTC trend_follow_entry 과거 검토안 (초기 이력, 날짜 미기록)

- 중간형
  - `BTC_TREND_ENABLE_TREND_FOLLOW_ENTRY=true`
  - `BTC_TREND_MIN_EMA_SPREAD_PCT=0.005`
  - `BTC_TREND_MIN_VOLUME_RATIO=1.00`
  - `BTC_TREND_MIN_ATR_PCT=0.07`
  - 의미: 너무 약한 상승 정렬 재진입은 줄이되, 골든크로스 외 추세 연장 진입 기회는 유지합니다.
- 보수형
  - `BTC_TREND_ENABLE_TREND_FOLLOW_ENTRY=true`
  - `BTC_TREND_MIN_EMA_SPREAD_PCT=0.010`
  - `BTC_TREND_MIN_VOLUME_RATIO=1.10`
  - `BTC_TREND_MIN_ATR_PCT=0.08`
  - 의미: 거래 수는 더 줄지만, 더 강한 추세 구간만 trend follow 진입을 허용합니다.
- 현재 적용에 더 가까운 최근 방향
  - `BTC_TREND_ENABLE_TREND_FOLLOW_ENTRY=true`
  - `BTC_TREND_MIN_EMA_SPREAD_PCT=0.015`
  - `BTC_TREND_MIN_VOLUME_RATIO=1.30`
  - `BTC_TREND_MIN_ATR_PCT=0.07`
  - 의미: 과거 검토안보다 한 단계 더 보수적으로 약한 추세 구간 진입을 줄이고, 순익 보호 익절과 함께 운영합니다.
- 완전 골든크로스형
  - `BTC_TREND_ENABLE_TREND_FOLLOW_ENTRY=false`
  - 의미: 상승 정렬 유지 구간 재진입을 끄고, 새 골든크로스 발생 시에만 진입합니다.
  - 특징: 가장 해석이 깔끔하지만 거래 횟수가 가장 적어질 가능성이 큽니다.

### 다음 수익률 개선 후보

- 1단계
  - `BTC Donchian + ATR` 설계안 초안 작성
  - `부분익절 후 잔량 전용 관리` 를 현재 BTC/XRP 구조에 실험할지 먼저 판단
- 2단계
  - 알트 `Bollinger Squeeze + 거래량 확장` 진입 실험안 작성
  - 최근 손절 심볼에 대해 MA 돌파 대비 손절 억제 효과를 백테스트로 비교
- 3단계
  - `레짐 전환형 전략 선택기` 를 현재 레짐 가드 위에 얹는 설계안 작성
  - `TRENDING`, `CHOPPY`, `LOW_ENERGY` 별 허용 전략을 정의
- 4단계
  - `Cross-Sectional Momentum 로테이션` 후보를 분석 수집 레이어에서 먼저 리포트화
  - 이후 매매 전략으로 확장할지 판단

### 알트 부분손절 / 부분익절 적용안

- 기본 원칙
  - 알트는 모든 코인에 한 번에 적용하지 않고, `부분익절/부분손절이 잘 맞는 심볼만 선택 적용`합니다.
  - 현재 로그 기준으로 `진입 품질이 상대적으로 안정적인 코인`부터 먼저 켜고, `진입 자체가 불안정한 코인`은 보류합니다.

- 1차 적용 추천 코인
  - 부분익절 우선: `ETH/USDT`, `ETH/KRW`, `XRP/KRW`
  - 부분손절 우선: `ETH/USDT`, `ETH/KRW`
  - 보류: `PI/USDT`, `DOGE/KRW`

- 코인별 판단 이유
  - `ETH`
    - 현재 체결 성과가 가장 안정적이라 일부 수익을 먼저 잠그는 구조와 궁합이 좋습니다.
  - `XRP`
    - 아직 체결 표본은 적지만, 수수료가 낮고 작은 수익을 자주 확보하는 방향이 맞을 가능성이 큽니다.
  - `PI`
    - 현재는 부분청산보다 `진입 품질 개선`이 우선입니다.
  - `DOGE`
    - 현재는 손절 빈도와 실패 돌파가 더 문제라, 부분손절/부분익절보다 `보수적 진입 유지`가 우선입니다.

- 추천 기본값
  - 부분익절 비율: `0.5`
  - 부분익절 발동: `현재 최소 익절률 도달 시`
  - 부분손절 비율: `0.5`
  - 부분손절 발동: `현재 손절률 도달 시`
  - 잔량 처리
    - 부분익절 후 잔량은 기존 익절/손절/추세종료 규칙 유지
    - 부분손절 후 잔량은 기존 손절/익절 규칙 유지

- .env 설계안
  - `STRATEGY_PARTIAL_TAKE_PROFIT_SYMBOLS=ETH/USDT,ETH/KRW,XRP/KRW`
  - `STRATEGY_PARTIAL_STOP_LOSS_SYMBOLS=ETH/USDT,ETH/KRW`
  - `STRATEGY_PARTIAL_TP_RATIO=0.5`
  - `STRATEGY_PARTIAL_SL_RATIO=0.5`

- 적용 순서
  - 1단계
    - `ETH/USDT`, `ETH/KRW`에 부분익절 먼저 적용
  - 2단계
    - `ETH/USDT`, `ETH/KRW`에 부분손절 적용
  - 3단계
    - `XRP/KRW`에 부분익절 확대
  - 4단계
    - 충분한 로그 후 `PI`, `DOGE` 재검토

### 1. 안전형 개선

- 하루 최대 거래 횟수 제한
- 시간대 필터 추가
- 일일 최대 수익 도달 시 거래 중단 같은 보수 규칙 추가

### 2. 중간형 개선

- 현재 이동평균 돌파 전략에 RSI 필터 추가
- 추가 매수 횟수별로 진입 비율을 다르게 조절
- 코인별 거래량/변동성 기준 세분화
- 상위 타임프레임을 5분봉 외에도 15분봉까지 비교하는 다중 필터 실험

### 3. 공격형 개선

- 더 짧은 주기에서 매매
- 볼린저밴드, RSI, 거래량을 조합한 단기 진입
- 그리드 전략 또는 박스권 전략 추가 실험

## 추후 검토 우선순위

1. 현재 전략으로 로그와 체결 결과를 충분히 관찰하기
2. 코인별 스킵 사유와 필터 통과율을 먼저 확인하기
3. 코인별 이격도, 익절률, 손절률이 적절한지 점검하기
4. 거래량 필터와 변동성 필터 기준값을 로그 기반으로 조정하기
5. 체결 로그가 쌓이면 승률/손익비 기준으로 전략을 다시 평가하기
6. RSI, 시간대, 거래 횟수 제한 같은 다음 보조 필터를 검토하기

## 다음 분석 고도화 설계

### 1. 전략 버전 관리

- 전략 값을 바꿀 때마다 `strategy_version` 이름을 붙여서 비교합니다.
- 추천 예시
  - `btc_mid_v1`
  - `btc_mid_v2`
  - `alt_xrp_fast_v1`
  - `alt_doge_safe_v1`
- 최소 기록 항목
  - 적용 시작 시각
  - 변경한 값
  - 변경 이유
  - 기대 효과
- 기록 위치
  - `STRATEGY_DECISIONS.md`
  - 체결 로그 `extra.strategy_version`

### 2. 주간 리포트 기준

- 전략 성과
  - 총 거래 수
  - 승률
  - 평균 순손익률
  - 총 순손익
  - 심볼별 손익
- 거래 품질
  - 평균 MFE
  - 평균 MAE
  - 평균 보유시간
  - 트레일링 활성화 비율
  - 트레일링 활성화 후 평균 유지시간
- 병목 분석
  - top block reason TOP 5
  - ready 대비 filled 비율
  - 심볼별 주요 차단 단계
- 시간대 성과
  - 시간대별 거래 수
  - 시간대별 평균 순손익
- 최종 판단
  - `유지`
  - `추가 관찰`
  - `조정 필요`

### 3. 백테스트 최소 설계

- 입력 데이터
  - OHLCV
  - 수수료
  - 최소 주문 금액/수량
  - 전략 파라미터
  - 심볼 목록
- 출력 지표
  - 체결 수
  - 승률
  - 평균 손익률
  - 최대 낙폭
  - 평균 MFE / MAE
  - 청산 사유 비율
  - 시간대별 성과
- 필수 반영 요소
  - 수수료
  - 분할 진입/청산
  - 손절 / 익절 / 트레일링
  - 상위 타임프레임 필터
- 운영 순서
  1. 최근 2주~4주 데이터 백테스트
  2. 가장 나아 보이는 파라미터 선정
  3. 실거래 소액 검증
  4. 실거래와 백테스트 차이 비교

### 4. 권장 실행 순서

1. 전략 버전 이름을 붙여 변경 이력을 남기기
2. 주간 리포트 기준으로만 성과 판단하기
3. BTC 전략부터 백테스트 초안 만들기
4. 그 다음 XRP, DOGE 순으로 확대하기
5. PI 와 ETH 는 로그가 더 쌓인 뒤 별도 평가하기
