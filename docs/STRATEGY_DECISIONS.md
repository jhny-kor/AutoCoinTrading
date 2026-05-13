# 전략 변경 근거 기록

이 문서는 전략이나 설정 값을 수정할 때, 어떤 로그와 어떤 관찰을 근거로 바꿨는지를 간단히 남기는 기록입니다.

## 기록 목적

- 나중에 "왜 이 값을 이렇게 바꿨는지"를 다시 추적할 수 있게 합니다.
- 감으로 바꾼 것과 로그 근거로 바꾼 것을 구분합니다.
- 다음 튜닝 때 같은 실수를 반복하지 않도록 돕습니다.

## 기록 규칙

- 제목 뒤에 가능한 범위에서 `날짜` 또는 `관련 버전`을 함께 적습니다.
- 오래된 항목 중 정확한 날짜를 모르면 `초기 이력, 날짜 미기록`으로 표시합니다.
- 현재 운영 기준과 다를 수 있는 항목도 삭제하지 않고, 당시 판단 근거를 남기는 쪽을 우선합니다.

## 현재까지의 주요 변경 기록

### 1. BTC를 전용 EMA + ATR 전략으로 분리 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `BTC/USDT`, `BTC/KRW`는 별도 BTC 전용 봇으로 분리
  - `PI/USDT`, `XRP/KRW`는 기존 알트 봇에 남김
- 근거 로그:
  - `BTC/USDT`, `BTC/KRW`는 평균 이격도와 평균 절대 변화율이 매우 낮았음
  - 기존 1분봉 MA 크로스 전략에서 `ready 0`, `filled 0` 구간이 길게 이어졌음
  - 반대로 `PI/USDT`는 평균 이격도와 변동성이 더 커서 같은 전략이라도 성격이 달랐음
- 해석:
  - BTC는 느린 추세형 전략이 더 적합하고, 알트는 단기 분할형 전략이 더 적합하다고 판단

### 2. BTC 진입 조건 완화 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `trend_follow_entry` 허용
  - `BTC_TREND_CONFIRM_EMA_PERIOD` 조정
  - `BTC_TREND_MIN_VOLUME_RATIO`, `BTC_TREND_MIN_ATR_PCT` 완화
- 근거 로그:
  - BTC 구조화 로그에서 `no_bullish_signal` 비중이 매우 높았음
  - 실제 주문 실패보다 "진입 조건 자체가 거의 성립하지 않음"이 병목이었음
  - 업비트 BTC는 매수 신호 직전까지 가는 경우가 있었고, 조금만 완화하면 실제 진입 가능성이 보였음
- 해석:
  - BTC는 손절보다 먼저 "신호가 너무 적어 거래 자체가 안 되는 문제"를 해결해야 했음

### 3. BTC 익절 개시를 앞당김 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `BTC_TREND_TAKE_PROFIT_ATR_MULTIPLE`를 낮춤
  - 익절 개시는 수수료 하한선보다 낮지 않게 제한
  - 전량 트레일링 익절 추가
- 근거 로그:
  - 실제 BTC 체결 후 `trend_exit`, `stop_loss`로 먼저 끝나는 사례가 나왔음
  - 진입 후 수익 구간이 잠깐 나와도 트레일링이 켜지기 전에 꺾이는 패턴이 보였음
  - "익절 타이밍이 느리다"는 사용자 체감과 실제 손익 흐름이 일치했음
- 해석:
  - BTC는 손절이 너무 빠르다기보다 익절 개시가 늦은 쪽이 문제였음

### 4. XRP는 더 활발하게, PI는 더 보수적으로 분리 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `XRP/KRW`
    - 이격도 완화
    - 최소 익절률 완화
    - 손절률 소폭 축소
  - `PI/USDT`
    - 이격도 강화
    - 최소 익절률 상향
    - 손절률 소폭 축소
- 근거 로그:
  - `XRP/KRW`는 거래량과 상위 추세가 괜찮아도 `distance_too_small`, `volatility_out_of_range`, `no_bullish_signal`에 자주 막힘
  - `XRP/KRW`는 실제로 수익률이 익절 근처까지 와도 매도 보류가 발생했음
  - `PI/USDT`는 변동성이 크고 거래량/상위 추세가 약한 구간이 자주 보여, 너무 공격적으로 돌리기 어려웠음
- 해석:
  - XRP는 "수수료를 넘는 작은 이익을 자주 먹는 구조"
  - PI는 "움직임은 크지만 신호 품질이 더 중요해서 보수적으로 진입/청산"

### 5. 알트에 보수형 trend follow 진입 추가 (초기 이력, 날짜 미기록)

- 변경 내용:
  - 골든크로스가 아니어도 아래 조건이면 제한적으로 진입 후보 허용
    - 현재 종가 > 현재 MA
    - 직전 종가 > 직전 MA
    - 현재 종가 > 직전 종가
- 근거 로그:
  - 알트 구조화 로그에서 `no_bullish_signal` 비중이 지나치게 높았음
  - 실제로는 MA 위에서 천천히 이어지는 구간이 있는데, "딱 한 번의 골든크로스"만 보는 구조라 신호를 자주 놓쳤음
  - `XRP/KRW`에서는 trend follow 추가 후 실제 진입 후보 로그가 확인됐음
- 해석:
  - 공격형이 아니라, "이미 위에 있는 추세를 보수적으로 이어서 보는 진입 보완"이 필요했음

### 6. ETH, DOGE를 분석 전용 수집 대상에 추가 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `ANALYSIS_OKX_SYMBOLS=ETH/USDT,DOGE/USDT`
  - `ANALYSIS_UPBIT_SYMBOLS=ETH/KRW,DOGE/KRW`
- 근거 로그:
  - `analysis_logs`에 소량 흔적은 있었지만 계속 추적되는 구조가 아니었음
  - 사용자 요청으로 알트군 확장 관찰 필요성이 생김
- 해석:
  - 아직 매매 대상은 아니지만, 장기적으로 어떤 알트가 현재 구조와 맞는지 비교하기 위해 수집 범위를 넓힘

### 7. DOGE/KRW 손절 빈도 감소를 위한 보수 조정 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `DOGE/KRW` 이격도 `0.15 -> 0.20`
  - `DOGE/KRW` 최소 익절률 `0.40 -> 0.50`
  - `DOGE/KRW` 손절률 `0.90 -> 1.30`
  - `DOGE/KRW` 전용 최소 거래량 배수 `1.20` 추가
- 근거 로그:
  - `trade_logs/trade_history.jsonl` 에서 `DOGE/KRW` 손절 거래가 두 번 연속 확인됨
  - 두 거래 모두 `143 -> 141`로 정리되어 실현 손익이 약 `-1.3986%`였음
  - `analysis_logs` 기준 `DOGE/KRW` 평균 절대 변화율이 약 `0.24%`, 평균 캔들 고저폭이 약 `0.29%`로 1분봉 흔들림이 큰 편이었음
  - 구조화 거래 로그에서는 진입 필터 대부분이 통과했는데도 직후 되밀리는 실패 돌파 패턴이 보였음
- 해석:
  - DOGE는 손절 로직이 잘못됐다기보다 `진입이 조금 느슨하고 손절이 코인 변동성 대비 좁은 상태`였음
  - 따라서 손절만 넓히지 않고, `진입 품질을 더 높이는 방향 + 손절 소폭 완화`를 같이 적용하는 쪽이 더 자연스럽다고 판단

### 8. DOGE/KRW를 한 단계 더 보수적으로 조정 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `DOGE/KRW` 전용 최소 거래량 배수 `1.20 -> 1.50`
  - `DOGE/KRW` 이격도 `0.20 -> 0.30`
  - `DOGE/KRW` 최소 익절률 `0.50 -> 0.60`
- 근거 로그:
  - 두 번의 손절 거래가 모두 비슷한 가격대(`143` 부근)에서 진입 후 `141`로 정리됨
  - 직전 로그에서도 DOGE는 이격도와 변동성은 충분하지만, 거래량이 매우 약하거나 상위 추세가 금방 꺾이는 구간이 반복됨
  - 즉 "들어간 뒤 버티기"보다 "들어가기 전에 더 강한 구간만 고르기"가 우선이라고 판단
- 해석:
  - DOGE는 잦은 재진입보다 `강한 거래량 + 더 벌어진 이격도`가 있을 때만 잡는 쪽이 손절 빈도 감소에 더 유리함
  - 익절률도 소폭 높여, 수수료를 넘긴 뒤 너무 빠르게 소액 청산되는 것보다 조금 더 질 좋은 수익 구간을 기다리도록 조정

### 9. TRUMP를 양 거래소 분석 수집 대상에 추가 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `ANALYSIS_OKX_SYMBOLS` 에 `TRUMP/USDT` 추가
  - `ANALYSIS_UPBIT_SYMBOLS` 에 `TRUMP/KRW` 추가
- 근거 로그:
  - 최근 1주 거래대금 상위 후보를 공식 거래소 공개 API로 확인했을 때, `TRUMP/USDT`, `TRUMP/KRW`가 모두 상위권에 위치했음
- 해석:
  - 아직 실거래 대상으로 바로 넣기보다, 변동성과 신호 품질을 먼저 비교할 수 있도록 분석 수집만 시작하는 쪽이 안전하다고 판단

### 10. BTC 트레일링을 중간형으로 강화 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `BTC_TREND_TAKE_PROFIT_ATR_MULTIPLE` `1.8 -> 1.6`
  - `BTC_TREND_TRAILING_DRAWDOWN_PCT` `0.6 -> 0.5`
- 근거 로그:
  - 최근 BTC 거래는 수익 구간에 잠깐 들어갔다가 다시 밀리는 패턴이 반복됐음
  - `trailing_armed` 이후 `trend_exit`가 먼저 끊는 문제는 이미 제거했고, 다음 단계로는 익절 보호를 조금 더 빠르게 거는 쪽이 자연스럽다고 판단
- 해석:
  - 공격적으로 너무 빠르게 잠그기보다, `수익 보호는 강화하되 추세 추종 성격은 유지하는 중간형`이 현재 표본과 가장 잘 맞는다고 봄

### 11. ETH 진입 조건 보수 완화 (초기 이력, 날짜 미기록)

- 변경 내용:
  - `ETH/USDT` 이격도 기준 `0.15 -> 0.08`
  - `ETH/KRW` 이격도 기준 `0.15 -> 0.08`
  - `ETH/USDT` 거래량 기준 `0.90 -> 0.60`
  - `ETH/KRW` 거래량 기준 `0.90 -> 0.60`
- 근거 로그:
  - `ETH/USDT` 최근 로그에서 이격도 `0.07% ~ 0.09%`, 거래량 배수 `0.61배` 수준으로 현재 기준 바로 아래에서 반복적으로 막힘
  - `ETH/KRW` 최근 로그에서도 이격도 `0.08% ~ 0.11%`, 거래량 배수 `0.56배` 수준으로 비슷한 병목이 확인됨
  - 다만 두 거래소 모두 상위 타임프레임은 하락 쪽이라, 상위 추세 필터는 그대로 유지함
- 해석:
  - ETH는 현재 전략에서 `전혀 움직이지 않는 코인`이라기보다, `신호 직전까지는 오지만 이격도와 거래량 기준 바로 아래에서 자주 탈락하는 코인`에 가까움
  - 그래서 상위 추세 역행 진입은 막되, 직전 병목만 보수적으로 완화해 실제 진입 후보가 생기는지 먼저 관찰하기로 함

### 12. ETH 최소 주문 수량과 주문 실행 품질 로그 보강 (2026-03-17, alt_live_v1)

- 변경 내용:
  - `STRATEGY_MIN_ORDER_AMOUNT_MAP` 에 `ETH/USDT:0.0001` 추가
  - 체결 로그에 주문 ID, API 지연, 슬리피지, 체결 비율 같은 주문 실행 품질 지표 추가
- 근거 로그:
  - `ETH/USDT` 는 소량 잔고 매도 시 `Parameter sz error` 가 발생한 이력이 있었음
  - `ETH/KRW` 는 부분 매도 금액이 업비트 최소 주문 금액 5,000 KRW 미만이라 `under_min_total_market_ask` 에러가 발생했음
  - 기존에는 체결 결과는 남았지만, 실제 주문 응답 품질을 한 번에 비교하기 어려웠음
- 해석:
  - 낮은 시드 테스트에서는 전략 신호보다 `최소 주문 금액/수량`과 `실행 품질`이 실제 수익에 더 직접적으로 영향을 줄 수 있음
  - 따라서 주문 실패를 사전 차단하고, 주문 응답 품질도 구조적으로 남겨야 다음 조정이 쉬움

### 13. BTC 약한 추세 진입 축소와 순익 보호 익절 추가 (2026-03-17, btc_mid_v1)

- 변경 내용:
  - `BTC_TREND_MIN_EMA_SPREAD_PCT` `0.010 -> 0.015`
  - `BTC_TREND_MIN_VOLUME_RATIO` `1.20 -> 1.30`
  - `BTC_TREND_ENABLE_FEE_PROTECT_EXIT=true`
  - `BTC_TREND_FEE_PROTECT_MIN_NET_PNL_PCT=0.12`
  - 추세 약화 시 `profit_protect_take_profit` 로 빠르게 순익 보호 청산하도록 확장
- 근거 로그:
  - 최근 BTC 손절 거래는 `MFE` 가 매우 낮고, 진입 직후 바로 밀리는 패턴이 반복됐음
  - `trend_exit` 도 수익 보호보다 손실 확정으로 끝나는 경우가 많았음
  - `trailing_take_profit` 인데도 수수료를 제하면 순익이 거의 없거나 음수인 사례가 확인됐음
- 해석:
  - 문제는 손절이 넓어서라기보다 `약한 추세 유지 구간 진입` 이 많았던 쪽에 가까움
  - 그래서 진입 품질을 소폭 강화하고, 일단 수수료를 넘긴 이익은 추세 약화 시 빨리 잠그는 보호 장치가 필요하다고 판단

### 14. 알트에도 순익 보호 익절 확대 (2026-03-17, alt_live_v1)

- 변경 내용:
  - `STRATEGY_ENABLE_FEE_PROTECT_EXIT=true`
  - `STRATEGY_FEE_PROTECT_MIN_NET_PNL_PCT=0.20`
  - 알트가 수수료를 제하고도 순익인 상태에서 메인 하락 신호가 나오면 `profit_protect_take_profit` 으로 전량 청산하도록 확장
- 근거 로그:
  - `ETH/USDT`, `ETH/KRW` 는 오늘 장중 `MFE` 가 1% 이상 충분히 나왔는데도 최종 손절로 마감된 사례가 있었음
  - 즉 알트는 손절이 너무 빠른 문제라기보다, 수익 구간을 잠그지 못하고 다시 되돌려주는 문제가 더 크게 보였음
- 해석:
  - 알트는 BTC보다 변동성이 커서 분할 익절만으로는 장중 수익을 지키지 못하는 구간이 있음
  - 그래서 메인 추세가 꺾일 때는 최소 익절률보다 먼저, `수수료를 넘긴 순익 자체를 잠그는 장치`가 필요하다고 판단

### 15. 호가창 미시구조 수집 확대 (2026-03-17, analysis_log_collector)

- 변경 내용:
  - 호가창 최우선 호가 외에 상위 3/5호가 누적 잔량, 누적 금액, 깊이 비대칭, 체결 가정 슬리피지 지표까지 함께 기록
- 근거 로그:
  - 최근 거래 품질 분석에서 손익뿐 아니라 “약한 추세 구간에서 호가가 얼마나 얇았는지”를 더 보고 싶다는 요구가 생김
  - 차트만으로는 실제 진입 직전 유동성 질을 판단하기 어려웠음
- 해석:
- 특히 낮은 시드 테스트에서는 호가가 얕거나 스프레드가 넓은 구간이 실제 승률과 체감 손익을 함께 깎을 수 있음
- 따라서 차트 외 정보는 뉴스보다 먼저, `호가 깊이`와 `실행 품질` 쪽을 구조적으로 쌓는 것이 더 실전적이라고 판단

### 25. 2026-03-31 손절 억제용 진입 보수화 (2026-04-01, alt_live_v1 / btc_mid_v1)

- 변경 내용:
  - `ETH/USDT` 최소 거래량 배수 `0.60 -> 0.80`
  - `ETH/KRW` 최소 거래량 배수 `0.90 -> 1.05`
  - `BTC/KRW` 최소 EMA 스프레드 기준 `0.030` 추가
  - `BTC/KRW` CHOPPY 레짐 최소 거래량 배수 `1.80 -> 2.00`
  - `BTC_TREND_STOP_LOSS_REENTRY_COOLDOWN_SEC` `600 -> 900`
- 근거 로그:
  - `2026-03-31` 실거래는 매도 21건, 평균 순손익률 `-0.1978%`, 총 순손익 음수였음
  - 손절 4건의 `MFE` 가 각각 `0.20%`, `0.03%`, `0.05%`, `0.10%` 수준으로 매우 낮았음
  - 즉 손절까지 간 거래는 대부분 진입 직후 후속 탄력이 거의 없었고, 손절폭이 넓어서 새는 구조로 보기 어려웠음
- 해석:
  - 우선순위는 손절폭 확대가 아니라 `약한 추세 진입 자체를 덜 받는 것`
  - ETH, 업비트 BTC는 현재 환경에서 진입 품질을 더 높이는 쪽이 손절 억제에 더 직접적이라고 판단

### 26. 2026-04-01 수익 확대용 BTC/XRP 익절 완화 (2026-04-01, alt_live_v1 / btc_mid_v1)

- 변경 내용:
  - `BTC_TREND_PARTIAL_TAKE_PROFIT_RATIO` `0.50 -> 0.40`
  - `BTC_TREND_TAKE_PROFIT_ATR_MULTIPLE` `1.6 -> 1.8`
  - `BTC_TREND_TRAILING_DRAWDOWN_PCT` `0.5 -> 0.6`
  - `XRP/KRW` 순익 보호 최소 순익률 `0.12 -> 0.16`
  - `XRP/USDT` 순익 보호 최소 순익률 `0.18` 추가
- 근거 로그:
  - `2026-04-01` 실거래는 매도 17건, 승률 `76.5%`, 평균 순손익률 `+0.2527%`로 양호했음
  - 다만 수익 거래 다수에서 실현 순익이 `MFE` 의 `20% ~ 40%` 수준에 머물렀음
  - 예: `XRP/KRW` 순익 `+0.20%` 대 `MFE +0.94%`, `BTC/KRW` 트레일링 순익 `+0.15%` 대 `MFE +0.78%`
- 해석:
  - BTC, XRP 는 수익 자체는 나는데 보호 청산이 빨라 러너를 충분히 못 가져가는 구간이 보였음
  - 그래서 ETH 는 보수 유지, BTC/XRP 만 이익 보호를 조금 늦추는 비대칭 조정이 자연스럽다고 판단

### 27. 업비트 REST 조회 지연 완화용 짧은 캐시 추가 (2026-04-01, execution/upbit)

- 변경 내용:
  - `UPBIT_REQUEST_TIMEOUT_MS=10000`
  - `UPBIT_BALANCE_CACHE_TTL_SEC=1.0`
  - `UPBIT_ORDERBOOK_CACHE_TTL_SEC=0.8`
  - `UPBIT_BEST_BID_REFRESH_BUFFER_PCT=0.30`
  - 업비트 시장가 매도도 공통 재시도 경로 사용
  - 주문 직후 잔고/호가 캐시 무효화 추가
- 근거 로그:
  - 최근 이틀 평균 실행 품질은 `UPBIT api_latency_ms ≈ 1023ms`, `exchange_ack_latency_ms ≈ 548ms` 로 `OKX` 대비 크게 느렸음
  - 봇 루프 내부에서 잔고 조회, 호가 조회를 매 심볼마다 반복하는 구조라 지연과 429 리스크를 함께 키울 여지가 있었음
- 해석:
  - 업비트 주문 응답 자체를 코드만으로 빠르게 만들 수는 없지만, `중복 REST 호출` 은 줄일 수 있음
  - 짧은 TTL 캐시와 주문 후 캐시 무효화를 넣어, 실시간성은 유지하면서 같은 루프 안의 불필요한 조회를 줄이는 쪽이 가장 실용적이라고 판단

### 28. 레짐별 포지션 비중 1차 적용 (2026-04-03, alt_live_v1 / btc_mid_v1)

- 변경 내용:
  - 알트
    - `TRENDING:1.00`
    - `BREAKOUT_ATTEMPT:0.80`
    - `CHOPPY:0.40`
    - `LOW_ENERGY:0.00`
    - `OVERHEATED:0.20`
    - `EXHAUSTION_RISK:0.00`
  - BTC
    - `TRENDING:1.10`
    - `BREAKOUT_ATTEMPT:0.90`
    - `CHOPPY:0.50`
    - `LOW_ENERGY:0.00`
    - `OVERHEATED:0.30`
    - `EXHAUSTION_RISK:0.00`
- 근거 로그:
  - 최근 실거래는 같은 진입 규칙이어도 `LOW_ENERGY`, `CHOPPY`, `TRENDING` 구간에서 성격 차이가 분명했음
  - 손절이 난 구간은 대체로 약한 후속 탄력 레짐에 속했고, 수익 러너가 나온 구간은 `TRENDING` 쪽에 가까웠음
- 해석:
  - 레짐을 진입 차단뿐 아니라 `진입 크기 조절`에도 쓰는 것이 자연스럽다고 판단
  - 1차는 전략 규칙 자체를 크게 바꾸지 않고 포지션 크기만 조절해 효과를 관찰하는 쪽이 가장 안전하다고 봄

### 18. 부분 익절 후 재진입/추가매수 쿨다운 추가 (2026-03-18, alt_live_v1)

- 변경 내용:
  - `STRATEGY_PARTIAL_TP_REENTRY_COOLDOWN_SEC=900`
  - 부분 익절 직후 같은 코인 신규 재진입과 추가 매수를 일정 시간 차단
- 근거 로그:
  - 부분 익절 후 남은 포지션이 아직 불안정한 구간에서 다시 물량이 늘어나면, 방금 잠근 수익을 다시 되돌릴 수 있다는 우려가 있었음
- 해석:
  - 부분 익절은 리스크를 줄이는 행위인데, 직후 바로 재진입/추가매수가 열려 있으면 그 의미가 약해짐
  - 따라서 부분 익절 직후에는 짧은 관망 구간을 둬서 수익 보호 의도를 유지하는 편이 더 안전하다고 판단

### 19. BTC 수익성 청산 후 재진입/추가매수 쿨다운 추가 (2026-03-18, btc_mid_v1)

- 변경 내용:
  - `BTC_TREND_PROFIT_EXIT_REENTRY_COOLDOWN_SEC=600`
  - `trailing_take_profit`, `profit_protect_take_profit` 직후에는 신규 진입과 추가매수를 잠시 차단
- 근거 로그:
  - BTC는 부분 익절이 없지만, 수익성 청산 직후 다시 비슷한 자리에서 물량을 늘리면 막 잠근 수익을 다시 되돌릴 위험이 있었음
- 해석:
  - BTC는 알트보다 거래 빈도가 적으므로 지나치게 긴 쿨다운 대신 `10분` 수준의 보수적 쿨다운으로 시작하는 것이 적절하다고 판단

### 20. 복구 불가 포지션 보류와 OKX 주문 실패 비증폭 처리 (2026-03-28, runtime hardening)

- 변경 내용:
  - 네 봇 모두 재시작 후 `거래소에는 포지션이 있는데 trade_history 기반 평균 진입가를 복구하지 못한 경우`, 현재가로 임시 진입가를 만들지 않고 자동 매매를 보류하도록 변경
  - `OKX` 봇들은 주문 실패를 `order_failed` 로 기록한 뒤 다시 `loop_error` 로 재증폭하지 않고, 경고만 남기고 다음 루프로 진행하도록 변경
  - 리팩토링 전 원본은 `backups/refactor_20260328_p1_p2/` 아래에 별도 보관
- 근거 로그:
  - 기존 코드에서는 재시작 후 복구 실패 시 현재가를 평균 진입가로 임시 세팅해 손절/익절/순손익 판단이 왜곡될 수 있었음
  - `OKX` 쪽 주문 실패는 이미 `order_failed` 를 남긴 뒤 다시 예외를 올려 같은 실패가 `loop_error` 까지 이중 기록되는 패턴이 있었음
- 해석:
  - live 트레이딩에서는 잘못된 임시 진입가보다 `자동 매매 보류` 가 더 안전함
  - 주문 실패는 운영자가 원인 하나를 한 번만 해석할 수 있어야 하므로, 경고/루프 오류를 분리해 중복 알림을 줄이는 편이 더 실전적이라고 판단

### 20. BTC 1회 부분 익절 추가 (2026-03-19, btc_mid_v1)

- 변경 내용:
  - `BTC_TREND_ENABLE_PARTIAL_TAKE_PROFIT=true`
  - `BTC_TREND_PARTIAL_TAKE_PROFIT_RATIO=0.5`
  - 익절가 도달 시 1회 부분 익절 후 잔량은 기존 트레일링/순익 보호 규칙으로 관리
- 근거 로그:
  - BTC는 큰 추세를 오래 먹는 날도 있지만, 익절가 도달 뒤 되돌림이 생기며 수익이 많이 줄어드는 사례가 있었음
  - 따라서 전량 트레일링만 두기보다, 첫 수익 구간에서 일부를 먼저 잠그는 장치가 있으면 체감 수익 안정성이 높아질 수 있다고 판단
- 해석:
  - BTC도 알트처럼 과도한 분할 구조는 아니어야 하므로, `1회 50% 부분 익절 + 잔량 추세 추종` 정도가 가장 무난한 시작점이라고 봄

### 21. BTC 진입 필터 강화와 강한 상승 추세 pullback 허용 (2026-03-19, btc_mid_v1)

- 변경 내용:
  - `BTC_TREND_MIN_EMA_SPREAD_PCT` `0.015 -> 0.020`
  - `BTC_TREND_MIN_VOLUME_RATIO` `1.30 -> 1.45`
  - `BTC_TREND_ENABLE_BULL_PULLBACK_HOLD=true`
  - `BTC_TREND_BULL_PULLBACK_TOLERANCE_PCT=0.20`
  - `BTC_TREND_BULL_PULLBACK_MIN_SPREAD_PCT=0.10`
- 근거 로그:
  - 최근 BTC 손절 거래 상당수는 `MFE` 가 거의 없는 약한 진입이었음
  - 반대로 강한 상방 정렬 구간에서는 작은 조정에도 `trend_exit` 또는 보호 익절이 너무 빨리 나갈 가능성이 있었음
- 해석:
  - 진입은 더 보수적으로 줄이고, 대신 `상위 추세 동의 + EMA 정렬 + 충분한 스프레드 + 짧은 되돌림` 구간은 일시 조정으로 봐서 너무 성급한 청산을 줄이는 편이 더 자연스럽다고 판단

### 16. 목표 비중 + 누적 투입 원가 기반 포트폴리오 배분 추가 (2026-03-17, portfolio allocator)

- 변경 내용:
  - `BTC 60 / ETH 30 / XRP 10` 목표 비중을 기준으로 신규 매수 예산을 제한하는 포트폴리오 배분 로직 추가
  - 강제 매도 리밸런싱은 하지 않고, 신규 매수만 제한
  - 기존 보유분은 현재 평가금액이 아니라 `남아 있는 누적 투입 원가` 기준으로 계산
- 근거 로그:
  - 기존 `position_ratio` 방식은 코인별 신규 진입 크기를 조절할 뿐, 이미 많이 들어간 코인을 자동으로 덜 사는 구조가 아니었음
  - 특히 BTC 중심 운영 의도를 반영하려면, “현재 얼마를 넣었는지”를 기준으로 신규 매수 한도를 계산하는 편이 더 안정적이라고 판단
- 해석:
  - 낮은 시드 테스트에서는 평가손익보다 “실제 누적 투입 금액 통제”가 더 중요함
  - 따라서 총 지갑 금액은 현재 가용 현금과 남아 있는 누적 투입 원가를 합쳐 계산하고, 각 코인은 목표 비중을 넘지 않게 신규 진입만 제한하는 방식이 가장 안전하다고 봄

### 17. 거래량 강세 코인에 대한 보수적 동적 오버웨이트 설계 (2026-03-17, stage 2)

- 변경 내용:
  - 거래량과 추세 품질이 아주 강한 코인만 목표 비중을 일시적으로 `+5%` 확대할 수 있는 동적 오버웨이트 구조 추가
  - 확장 폭은 요청 범위인 `5~10%` 중 보수적으로 `5%`부터 시작
- 근거 로그:
  - 특정 코인은 거래량이 강하게 붙을 때 손절보다 익절 확률이 높아질 수 있다는 운영 아이디어가 있었음
  - 다만 한 번에 너무 큰 비중 확대는 과매수와 고점 추격 위험을 키울 수 있음
- 해석:
  - 2차 확장은 기본 비중을 깨는 공격형 기능이 아니라, `강한 구간에서만 약간 더 싣는 보조 장치`로 시작하는 것이 맞음
  - 따라서 조건은 엄격하게 두고, 최대 확대 폭도 `+5%` 수준으로 제한하는 보수형이 적절하다고 판단

### 18. BTC/USDT 진입 강화와 ETH/KRW 브레이크이븐 가드 추가 (2026-03-21, symbol tuning)

- 변경 내용:
  - `BTC/USDT` 에만 심볼별 진입 오버라이드를 추가해 EMA 스프레드와 거래량 기준을 더 엄격하게 적용
  - `ETH/KRW` 에만 브레이크이븐 가드를 추가해, 충분한 `MFE` 가 나온 뒤 순익이 거의 사라지고 약세 신호가 나오면 먼저 청산
- 반영 설정:
  - `BTC_TREND_MIN_EMA_SPREAD_PCT_MAP=BTC/USDT:0.030`
  - `BTC_TREND_MIN_VOLUME_RATIO_MAP=BTC/USDT:1.70`
  - `STRATEGY_BREAK_EVEN_GUARD_MIN_MFE_PCT_MAP=ETH/KRW:0.30`
  - `STRATEGY_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT_MAP=ETH/KRW:0.05`
- 근거 로그:
  - `BTC/USDT` 는 손실 거래 다수의 `MFE` 가 `0.0% ~ 0.2%` 수준이라 약한 진입 제거가 우선이라고 판단
  - `ETH/KRW` 는 `MFE 0.3% ~ 2.0%` 구간이 있었는데도 최종 손절로 끝난 사례가 반복되어, 수익 보호 장치 강화가 더 효과적이라고 판단
- 해석:
  - BTC 쪽은 “덜 들어가고, 더 강한 자리만 받는 것”이 우선
  - ETH/KRW 쪽은 “좋은 수익 구간을 크게 다시 반납하지 않게 잠그는 것”이 우선

### 19. 업비트 429 완화와 KRW 주문 버퍼 추가 (2026-03-22, upbit stability)

- 변경 내용:
  - 업비트 공용 API 호출(`fetch_ohlcv`, `fetch_balance`, `fetch_order_book`)에 짧은 backoff 재시도 추가
  - 업비트 시장가 매수 시 KRW 잔고를 끝까지 쓰지 않도록 주문 버퍼 추가
  - BTC 업비트 추가매수 경로에서도 같은 버퍼 로직을 사용하도록 통일
- 반영 설정:
  - `UPBIT_REQUEST_RETRY_COUNT`
  - `UPBIT_REQUEST_RETRY_DELAY_SEC`
  - `UPBIT_KRW_ORDER_BUFFER_PCT`
  - `UPBIT_KRW_ORDER_BUFFER_KRW`
- 근거 로그:
  - `RateLimitExceeded ... 429 Too Many Requests`
  - `insufficient_funds_bid`
- 해석:
  - 업비트는 짧은 주기 다중 봇 운영에서 공개/인증 호출이 겹치면 429가 날 수 있어 공용 재시도 완화가 필요
  - 시장가 매수는 수수료와 잠금 금액 때문에 가용 KRW를 너무 타이트하게 쓰면 반복적으로 주문 실패가 날 수 있어 안전 버퍼가 필요하다고 판단

### 20. 저에너지 장 공통 가드와 BTC/KRW 추가 보수화 (2026-03-22, low energy gate)

- 변경 내용:
  - 분석 수집 로그의 최신 상태를 읽어 거래소별 평균 거래량 배수와 평균 절대 변화율이 낮으면 신규 진입을 차단하는 공통 저에너지 가드 추가
  - `BTC/KRW` 에만 심볼별 최소 ATR 기준을 더 높여 저변동 구간 진입을 줄이도록 조정
- 반영 설정:
  - `MARKET_GUARD_ENABLE_LOW_ENERGY`
  - `MARKET_GUARD_LOW_ENERGY_AVG_VOLUME_RATIO`
  - `MARKET_GUARD_LOW_ENERGY_AVG_ABS_CHANGE_PCT`
  - `MARKET_GUARD_LOW_ENERGY_REQUIRE_READY_COUNT_ZERO`
  - `MARKET_GUARD_LOW_ENERGY_MAX_RECORD_AGE_SEC`
  - `BTC_TREND_MIN_ATR_PCT_MAP=BTC/KRW:0.09`
- 근거 로그:
  - 오늘 최신 시장 상태는 운영 심볼 평균 거래량 배수 `0.632`, 평균 절대 변화율 `0.0475%`, 공개 기준 매수 준비 `0`
  - 오늘 `BTC/KRW` 실체결은 손절 2건뿐이었고 `MFE` 도 `0.074%`, `0.000%` 수준으로 매우 낮았음
- 해석:
  - 전체 시장 에너지가 약한 시간대엔 추세추종 단타가 잘 안 먹히므로 진입 자체를 줄이는 것이 우선
  - `BTC/KRW` 는 저변동 구간에서 준비 신호가 많아도 실제 수익 기여가 낮아 ATR 기준을 더 보수적으로 보는 편이 맞다고 판단

### 21. ETH/KRW 추가 보수화 (2026-03-25, eth krw tuning)

- 변경 내용:
  - `ETH/KRW` 심볼에 한해 거래량 기준, 최소 이격도, 브레이크이븐 가드 기준을 더 보수적으로 조정
- 변경 전 -> 변경 후:
  - `STRATEGY_MIN_VOLUME_RATIO_MAP`: `ETH/KRW 0.60 -> 0.90`
  - `STRATEGY_MIN_CROSSOVER_GAP_PCT_MAP`: `ETH/KRW 0.08 -> 0.12`
  - `STRATEGY_BREAK_EVEN_GUARD_MIN_MFE_PCT_MAP`: `ETH/KRW 0.30 -> 0.25`
  - `STRATEGY_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT_MAP`: `ETH/KRW 0.05 -> 0.10`
- 근거 로그:
  - 최근 `ETH/KRW` 진입은 `volume_ratio 0.61 ~ 0.90`, `gap_pct 0.085 ~ 0.12` 같은 얕은 구간에서도 발생
  - 브레이크이븐 가드가 작동한 일부 거래는 손실 확대를 막았지만, 순익이 거의 없는 수준에서 끝난 케이스도 있었음
- 해석:
  - ETH/KRW 는 아직 추세 지속력이 약한 구간에서도 들어가는 편이라 진입 자체를 더 선별해야 함
  - 동시에 브레이크이븐 가드는 더 이르게 켜되, 순익 바닥은 더 높게 잠가야 실질적인 손익 개선이 가능하다고 판단

### 22. XRP/KRW 및 BTC CHOPPY 구간 추가 보수화 (2026-03-26, xrp btc conservative tuning)

- 변경 내용:
  - `XRP/KRW` 는 상위 타임프레임이 하락 추세일 때 신규 진입을 차단
  - `XRP/KRW` 거래량 기준을 소폭 상향
  - BTC 는 `CHOPPY` 레짐에서 심볼별 추가 최소 거래량 기준을 적용
- 변경 전 -> 변경 후:
  - `STRATEGY_BLOCK_ENTRY_WHEN_HTF_BEARISH_SYMBOLS`: `미사용 -> XRP/KRW`
  - `STRATEGY_MIN_VOLUME_RATIO_MAP`: `XRP/KRW 기본값 사용 -> XRP/KRW 1.10`
  - `BTC_TREND_CHOPPY_MIN_VOLUME_RATIO_MAP`: `미사용 -> BTC/USDT 1.90, BTC/KRW 1.70`
- 근거 로그:
  - `2026-03-26 XRP/KRW` 손실 거래는 `volume_ratio 4.55`였지만 `htf_bearish=True` 상태에서 최종 `-1.33%` 순손실로 마감
  - `2026-03-26 BTC/KRW`, `BTC/USDT` 손실 거래는 모두 `CHOPPY` 또는 `LOW_ENERGY` 구간에서 `MFE` 가 매우 낮았음
- 해석:
  - XRP/KRW 는 순간 거래량만 강해도 상위 하락 추세에 다시 눌리는 경우가 있어 상위 추세 역행 진입을 더 강하게 막는 편이 맞음
  - BTC 는 `CHOPPY` 구간에서 기존 거래량 기준만으로는 약한 진입을 충분히 거르지 못해 레짐별 추가 거래량 기준이 필요하다고 판단

### 23. ETH/USDT 상위 하락 추세 차단 및 BTC CHOPPY 기준 소폭 상향 (2026-03-27, eth usdt guard and btc mild tighten)

- 변경 내용:
  - `ETH/USDT` 도 `htf_bearish=True`일 때 신규 진입 차단 대상에 추가
  - BTC 는 `CHOPPY` 레짐 추가 거래량 기준만 소폭 상향
- 변경 전 -> 변경 후:
  - `STRATEGY_BLOCK_ENTRY_WHEN_HTF_BEARISH_SYMBOLS`: `XRP/KRW -> XRP/KRW,ETH/USDT`
  - `BTC_TREND_CHOPPY_MIN_VOLUME_RATIO_MAP`: `BTC/USDT 1.90 -> 2.00`, `BTC/KRW 1.70 -> 1.80`
- 근거 로그:
  - `2026-03-27 ETH/USDT` 손실 2건은 모두 `htf_bearish=True` 상태였고, 장중 `MFE` 는 약 `0.49%`까지 있었지만 최종 `-1.11%`, `-1.24%` 순손실로 마감
  - `2026-03-27 BTC/KRW`, `BTC/USDT` 손실은 여전히 `CHOPPY/LOW_ENERGY` 구간에서 낮은 `MFE` 패턴이 반복
- 해석:
  - `ETH/USDT` 는 상위 하락 추세 역행 진입을 더 강하게 차단하는 편이 맞음
  - BTC 는 이미 많이 보수화된 상태라, 추가 조정은 `CHOPPY` 구간 거래량 기준만 소폭 높이는 정도가 적절하다고 판단

### 24. ETH/USDT 수익 보호 조기화 (2026-03-29, eth usdt profit protection tighten)

- 변경 내용:
  - `ETH/USDT` 는 순익 보호 익절 기준을 더 낮추고, 브레이크이븐 가드는 더 빨리 켜되 순익 바닥은 더 높게 요구하도록 조정
- 변경 전 -> 변경 후:
  - `STRATEGY_FEE_PROTECT_MIN_NET_PNL_PCT_MAP`: `ETH/USDT 0.12 -> 0.08`
  - `STRATEGY_BREAK_EVEN_GUARD_MIN_MFE_PCT_MAP`: `ETH/USDT 0.18 -> 0.12`
  - `STRATEGY_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT_MAP`: `ETH/USDT 0.08 -> 0.20`
- 근거 로그:
  - `2026-03-28 ETH/USDT` 실거래는 장중 `MFE +4.53%`까지 갔지만 최종 `-0.2781%` 순손실로 종료
  - 같은 날짜 백테스트는 `break_even_guard_exit` 로 `+0.0374%`로 마감
- 해석:
  - 실거래는 수익 보호 신호가 너무 늦어 장중 수익 대부분을 되돌렸다고 판단
  - 따라서 `ETH/USDT` 는 다른 알트보다 더 빠르게 보호를 켜고, 음수로 내려가기 전 더 높은 순익 구간에서 정리하는 편이 맞음

### 25. BTC Donchian / 알트 Squeeze 모드 활성화 (2026-04-18, entry mode activation)

- 변경 내용:
  - BTC 기본 진입 모드를 `ema` 에서 `donchian` 으로 전환
  - 알트 기본 진입 모드를 `ma` 에서 `squeeze` 로 전환
  - 운영 로그에서 Donchian / Bollinger 지표값이 `N/A` 로 명확히 보이도록 문구 보정
- 변경 전 -> 변경 후:
  - `BTC_TREND_ENTRY_MODE`: `ema -> donchian`
  - `BTC_TREND_DONCHIAN_ENTRY_LOOKBACK`: `미설정 -> 20`
  - `BTC_TREND_DONCHIAN_EXIT_LOOKBACK`: `미설정 -> 10`
  - `BTC_TREND_DONCHIAN_CONFIRM_BREAKOUT_CLOSE`: `미설정 -> true`
  - `STRATEGY_ENTRY_MODE`: `ma -> squeeze`
  - `STRATEGY_BB_PERIOD`: `미설정 -> 20`
  - `STRATEGY_BB_STDDEV`: `미설정 -> 2.0`
  - `STRATEGY_SQUEEZE_MAX_BANDWIDTH_PCT`: `미설정 -> 0.60`
  - `STRATEGY_SQUEEZE_MIN_VOLUME_RATIO`: `미설정 -> 1.80`
- 근거 로그:
  - 최근 4일 BTC 는 `partial_take_profit / trailing_take_profit` 쪽은 살아 있지만 약한 EMA 크로스 노이즈가 계속 관찰됨
  - 최근 알트 로그에서는 BB Width 가 `0.34% ~ 0.51%` 구간으로 자주 나타나 밴드 수축 구간 선별이 가능했고, 후속 탄력 없는 MA 진입을 줄일 여지가 있었음
- 해석:
  - BTC 는 Donchian 돌파 기반으로 추세 노이즈를 줄이고 추세 러너를 더 길게 가져가는 방향을 우선 실험
  - 알트는 Bollinger Squeeze + 거래량 확장 돌파로 진입 빈도를 줄이되, 후속 탄력 없는 약한 진입을 줄이는 방향으로 전환

### 25. 레짐별 포지션 비중 1차 적용 (2026-04-03, alt_live_v1 / btc_mid_v1)

- 변경 내용:
  - 알트 `STRATEGY_REGIME_POSITION_SCALE_MAP` 적용
  - BTC `BTC_TREND_REGIME_POSITION_SCALE_MAP` 적용
  - 레짐별 포지션 비중 스케일을 로그와 metrics 에 함께 기록
- 근거 로그:
  - 최근 손절 거래는 `CHOPPY`, `LOW_ENERGY` 구간에서 후속 탄력이 약한 패턴이 반복
  - 반대로 수익 러너가 나온 거래는 `TRENDING` 쪽에서 더 잘 유지되는 흐름이 확인
- 해석:
  - 레짐을 단순 진입 차단뿐 아니라 `진입 크기 조절`에도 쓰는 편이 자연스럽다고 판단

### 26. BTC LOW_ENERGY 기준 알트 신규 진입 비중 축소 추가 (2026-04-03, alt_live_v1)

- 변경 내용:
  - `STRATEGY_ENABLE_BTC_REGIME_POSITION_SCALING=true`
  - `STRATEGY_BTC_REGIME_POSITION_SCALE_MAP=LOW_ENERGY:0.50`
  - `STRATEGY_BTC_REGIME_POSITION_SCALE_OVERRIDE_MAP`
    - `ETH/KRW|LOW_ENERGY:0.35`
    - `XRP/KRW|LOW_ENERGY:0.60`
    - `ETH/USDT|LOW_ENERGY:0.35`
    - `XRP/USDT|LOW_ENERGY:0.60`
- 근거 로그:
  - 최근 3일 업비트 알트 실거래 캠페인 10건 기준 기본 승률은 `60.0%`, 평균 순손익률은 `-0.1072%`
  - 같은 표본에서 `BTC regime != LOW_ENERGY` 조건만 유지하면 승률 `83.3%`, 평균 순손익률 `+0.1380%`
  - 다만 `LOW_ENERGY`를 바로 하드 차단하면 수익 거래도 함께 줄어드는 구간이 있어 1차는 `차단`보다 `비중 축소`가 더 안전하다고 판단
- 해석:
  - 최근 손실 거래는 BTC가 `LOW_ENERGY`일 때 상대적으로 더 많았음
  - ETH는 손절 억제가 더 중요하고, XRP는 러너 보존도 중요해 `ETH 더 보수 / XRP 덜 보수`의 비대칭 축소가 적절하다고 판단

### 27. BTC ATR 퍼센트 기반 알트 신규 진입 비중 축소 추가 (2026-04-03, alt_live_v1)

- 변경 내용:
  - `STRATEGY_ENABLE_BTC_ATR_POSITION_SCALING=true`
  - `STRATEGY_BTC_ATR_POSITION_SCALE_LOOKBACK=14`
  - `STRATEGY_BTC_ATR_POSITION_SCALE_THRESHOLD_MAP=0.18:0.70,0.15:0.45,0.12:0.25`
  - 알트 신규 진입 비중에 `BTC atr_pct` 단계형 스케일을 추가 적용
- 근거 로그:
  - 최근 3일 업비트 알트 캠페인 10건 기준 `BTC atr_pct >= 0.18` 구간만 유지하면 승률 `80.0%`, 평균 순손익률 `+0.2937%`
  - 반대로 하드 차단으로 쓰면 수익 거래도 일부 함께 사라져, 최근 표본에서는 `차단`보다 `단계형 축소`가 더 적절했음
  - 운영 로그에서도 `BTC ATR(0.0257%) 스케일 0.25x` 형식으로 실제 적용값이 기록되는 것을 확인
- 해석:
  - BTC 변동성이 너무 낮은 구간은 알트 추세 추종 엣지가 떨어지는 경우가 많았음
  - 따라서 바로 진입 금지로 가기보다 `0.70x -> 0.45x -> 0.25x` 단계형 축소를 먼저 적용해 손실 진입을 줄이고, 좋은 거래까지 과하게 잘리지 않도록 조정

### 28. BTC ATR 퍼센트 기반 BTC 신규 진입 비중 축소 추가 (2026-04-04, btc_mid_v1)

- 변경 내용:
  - `BTC_TREND_ENABLE_ATR_POSITION_SCALING=true`
  - `BTC_TREND_ATR_POSITION_SCALE_THRESHOLD_MAP=0.16:0.80,0.13:0.60,0.10:0.35`
  - BTC 신규 진입 비중에도 `ATR 퍼센트` 기준 단계형 스케일을 추가 적용
- 근거 로그:
  - BTC는 이미 레짐별 포지션 스케일이 있었지만, 최근 `LOW_ENERGY`가 아니어도 `atr_pct`가 얕은 구간에서 신호 대비 후속 탄력이 약한 사례가 반복
  - 최근 업비트 BTC 로그에서도 `atr_pct 0.13%~0.14%` 수준이 자주 보였고, 이런 구간은 추세 추종 엣지가 낮은 편이었음
- 해석:
  - BTC도 단순 ON/OFF보다 `변동성이 얕을수록 비중을 줄이는 방식`이 더 자연스럽다고 판단
  - 즉 BTC는 `레짐 스케일 x ATR 스케일` 구조로 진입 크기를 더 부드럽게 조절

### 29. SOL 분석 수집 추가 (2026-04-04, analysis expansion)

- 변경 내용:
  - `ANALYSIS_OKX_SYMBOLS=SOL/USDT`
  - `ANALYSIS_UPBIT_SYMBOLS=SOL/KRW`
- 근거 로그:
  - SOL은 대형 알트라 유동성, 거래대금 측면에서 실거래 후보가 될 가능성이 높음
  - 다만 현재 전략에 바로 넣기엔 최근 `volume_ratio`, `avg_abs_change_pct`, `ready 빈도`, 최소 주문 적합성 같은 실측 표본이 부족했음
- 해석:
  - 바로 실거래보다 먼저 분석 수집을 통해 `SOL`의 최근 1분봉 전략 적합성을 확인하는 편이 안전
  - 관찰 지표가 충분히 쌓이면 업비트/OKX 모두 실거래 후보로 순차 전환

### 30. 2026-04-05 ~ 2026-04-08 손절 반복 완화 조정 (2026-04-08, alt_live_v1 / btc_mid_v1)

- 변경 내용:
  - BTC 진입 품질 강화
    - `BTC_TREND_SIGNAL_SCORE_MIN=62`
    - `BTC_TREND_ENTRY_CONFIRMATION_LOOPS=3`
    - `BTC_TREND_STOP_LOSS_REENTRY_COOLDOWN_SEC=1200`
    - `BTC_TREND_MIN_VOLUME_RATIO_MAP` 에 `BTC/KRW:1.55` 추가
    - `BTC_TREND_CHOPPY_MIN_VOLUME_RATIO_MAP=BTC/USDT:2.20,BTC/KRW:2.20`
    - `get_btc_regime_policy()` 에서 `CHOPPY` 는 신규 진입 차단으로 보수화
  - 알트 진입 보수화
    - `STRATEGY_BLOCK_ENTRY_WHEN_HTF_BEARISH_SYMBOLS` 에 `ETH/KRW` 추가
    - `ETH/KRW` 최소 거래량 배수 `1.05 -> 1.20`
    - `ETH/KRW` 포지션 비중 `0.70 -> 0.45`
    - `ETH/KRW` 최소 이격도 `0.12 -> 0.15`
  - XRP 보호 장치 조기화
    - `XRP/KRW` 최소 익절률 `0.45 -> 0.40`
    - `XRP/USDT` 최소 익절률 `0.60 -> 0.55`
    - `XRP/KRW` 순익 보호 최소 순익률 `0.16 -> 0.10`
    - `XRP/USDT` 순익 보호 최소 순익률 `0.18 -> 0.10`
    - `XRP/KRW`, `XRP/USDT` 브레이크이븐 가드 최소 MFE `0.18` 추가
    - `XRP/KRW` 브레이크이븐 가드 순익 바닥 `0.04` 추가
    - `XRP/USDT` 브레이크이븐 가드 순익 바닥 `0.05` 추가
  - 알트 백테스트 parity 보강
    - `tools/backtest_replay.py` 에서 live 와 같은 `entry_mode`, `Bollinger squeeze 입력`, `fresh cross`, `HTF bearish 차단`을 반영
- 근거 로그:
  - `2026-04-05 ~ 2026-04-08` 실거래 기준 `stop_loss` 가 `18건`으로 가장 많았음
  - `OKX BTC/USDT` 손실 거래 평균 `MFE 0.1422%`, `MAE -0.1954%`
  - `UPBIT BTC/KRW` 손실 거래 평균 `MFE 0.0654%`, `MAE -0.1821%`
  - 즉 BTC는 손절폭보다 `진입 직후 후속 탄력 부족` 문제가 더 컸음
  - `ETH/KRW` 는 손실 거래 평균 `MFE 0.1916%`, `MAE -0.5997%` 로 작은 반등 후 빠르게 밀리는 패턴이 반복
  - `XRP/KRW`, `XRP/USDT` 는 승률이 나쁘지 않아도 `profit_protect` 수익보다 `stop_loss` 1~2건 손실이 더 크게 남는 구조였음
  - 최근 주간 배치 비교에서 알트 다수 심볼은 `백테스트 0건 / 실거래 체결 존재` 상태라 live parity 보강이 필요했음
- 해석:
  - BTC는 더 자주 들어가는 것보다 `애매한 EMA 정렬 유지 구간을 덜 잡는 것`이 우선이라고 판단
  - `ETH/KRW` 는 청산 최적화보다 진입 자체를 줄이는 편이 먼저라고 판단
  - `XRP` 계열은 손절을 넓히는 것보다 `조금 유리해졌을 때 더 빨리 지키는 구조`가 더 적합하다고 판단
  - 알트 백테스트는 live 와 같은 진입 퍼널을 더 많이 반영해야 이후 튜닝 신뢰도가 올라간다고 판단

### 31. 볼린저 밴드 계산 런타임 예외 수정 (2026-04-08, bugfix)

- 변경 내용:
  - `core/strategy/indicators.py` 에 `import math` 추가
- 근거 로그:
  - `ma_crossover_bot.log`, `upbit_ma_crossover_bot.log` 에서 `NameError: name 'math' is not defined` 반복 발생
  - 예외 위치는 `calc_bollinger_bands()` 의 `math.sqrt(variance)` 호출이었음
- 해석:
  - 전략 조정보다 먼저 런타임 예외를 제거해야 알트 봇 로그와 체결이 정상적으로 쌓임

### 32. 손절 후 패턴 기반 재진입 게이트 도입 (2026-04-09, alt_live_v1 / btc_mid_v1)

- 변경 내용:
  - BTC
    - `BTC_TREND_ENABLE_STOP_LOSS_PATTERN_REENTRY=true`
    - `BTC_TREND_STOP_LOSS_PATTERN_MIN_COOLDOWN_SEC=180`
    - `BTC_TREND_STOP_LOSS_PATTERN_MIN_SIGNAL_SCORE=72`
    - `BTC_TREND_STOP_LOSS_PATTERN_REQUIRE_CONFIRM_BULLISH=true`
    - `BTC_TREND_STOP_LOSS_PATTERN_REQUIRE_FRESH_CROSS=true`
  - 알트
    - `STRATEGY_ENABLE_STOP_LOSS_PATTERN_REENTRY=true`
    - `STRATEGY_STOP_LOSS_PATTERN_MIN_COOLDOWN_SEC=180`
    - `STRATEGY_STOP_LOSS_PATTERN_MIN_SIGNAL_SCORE=70`
    - `STRATEGY_STOP_LOSS_PATTERN_MIN_VOLUME_RATIO_MULTIPLIER=1.2`
    - `STRATEGY_STOP_LOSS_PATTERN_REQUIRE_HTF_BULLISH=true`
    - `STRATEGY_STOP_LOSS_PATTERN_REQUIRE_FRESH_CROSS=true`
  - 공통 구현
    - BTC/알트 공통 helper 추가
    - 손절 시각 복구/런타임 상태에 `last_stop_loss_at` 포함
    - 퍼널에 `stop_loss_reentry` 단계와 reason 코드 `stop_loss_pattern_reentry_blocked` 추가
    - live 봇 4개와 테스트에 반영
- 근거 로그:
  - 기존에는 손절 후 `쿨다운 시간만 지나면` 다시 진입 후보로 들어갈 수 있었음
  - 최근 손절 반복 구간을 보면, 시간은 충분히 지났어도 실제로는
    - BTC: `confirm_bullish=false`, `fresh_cross=false`, `signal_score<72`
    - 알트: `HTF 상승=false`, `fresh_cross=false`, `signal_score<70`
    가 반복됐음
  - 즉 문제는 쿨다운 시간보다 `패턴이 아직 복구되지 않았는데 다시 진입하려는 것`에 더 가까웠음
- 현재 관찰:
  - 2026-04-09 오전 로그 기준으로 gate 는 의도대로 동작 중
  - `BTC/USDT`, `BTC/KRW` 는 대부분 `confirm=false`, `fresh_cross=false`, 낮은 `signal_score` 때문에 막힘
  - `XRP/USDT`, `XRP/KRW`, `ETH/KRW` 는 거래량이 살아나는 순간이 있어도 `HTF 상승=false` 와 `fresh_cross=false` 때문에 막힘
  - 따라서 현재는 “좋은 재진입을 과도하게 막는다”기보다 “회복 전 재진입을 정확히 막는다”에 가까움
- 해석:
  - 완전한 시간 기반보다 `최소 시간 + 패턴 복구` 구조가 손절 반복 억제에 더 적합하다고 판단
  - 다만 이후 로그에서 `좋은 재진입도 자주 막는지`를 하루 이상 더 관찰한 뒤
    - BTC `72 -> 68`
    - 알트 `70 -> 65`
    같은 완화는 별도 검토 가능

### 33. Score 기반 동적 자본 배분 도입 (2026-04-09, portfolio)

- 변경 내용:
  - `PORTFOLIO_ENABLE_SCORE_BASED_SCALING=true`
  - `PORTFOLIO_SCORE_SCALE_MIN=0.60`
  - `PORTFOLIO_SCORE_SCALE_MAX=1.10`
  - `PORTFOLIO_SIGNAL_WEIGHT=0.40`
  - `PORTFOLIO_MARKET_WEIGHT=0.30`
  - `PORTFOLIO_EXECUTION_WEIGHT=0.20`
  - `PORTFOLIO_DIVERSIFICATION_WEIGHT=0.10`
  - 점수 버킷
    - `85+ -> 1.10`
    - `75+ -> 1.00`
    - `65+ -> 0.90`
    - `55+ -> 0.75`
    - `<55 -> 0.60`
  - 구현 범위
    - 알트/ BTC live 봇 4개
    - BTC add-on 배분
    - backtest replay
    - example config
    - allocation score 테스트
- 근거 로그:
  - 기존 구조는 `레짐/ATR/목표 비중` 축소는 잘 되지만, `좋은 심볼을 조금 더 / 나쁜 심볼을 조금 덜`을 하나의 점수로 설명하기 어려웠음
  - 2026-04-09 오전 로그 기준
    - `BTC/USDT` allocation score `약 42~50`
    - `BTC/KRW` allocation score `약 41~49`
    - `ETH/KRW`, `XRP/KRW`, `XRP/USDT` 도 `낮은 signal/market 점수`로 `score_scale=0.60`
    상태가 반복됨
  - 즉 최근 구간은 단순 신호보다 `시장 질`과 `실행 품질`, `분산 관점`까지 함께 축소하는 편이 더 자연스럽다고 판단
- 해석:
  - 이 구조는 공격적 확대보다 `나쁜 심볼 강한 축소`에 더 초점을 둠
  - 낮은 시드 테스트 환경에서는 이 방식이 기대손익보다 변동성 억제에 더 유리
  - 실제 로그에 `allocation_score`, `allocation_score_scale`, `allocation_reason_top` 이 남으므로 이후 튜닝 설명성도 좋아짐

### 34. XRP 보호 청산 상향 + BTC fresh cross 완화 예외 + score reason_top 수정 (2026-04-10)

- 변경 내용:
  - XRP 보호 청산 강화
    - `XRP/KRW` `break_even_guard_min_mfe_pct: 0.18 -> 0.15`
    - `XRP/USDT` `break_even_guard_min_mfe_pct: 0.18 -> 0.15`
    - `XRP/KRW` `break_even_guard_floor_net_pnl_pct: 0.04 -> 0.12`
    - `XRP/USDT` `break_even_guard_floor_net_pnl_pct: 0.05 -> 0.12`
  - BTC fresh cross 완화 예외
    - `BTC/USDT`
      - `300초 이상`
      - `confirm_bullish=true`
      - `signal_score >= 85`
      - 이면 `fresh_cross` 없이도 재진입 허용
    - `BTC/KRW`
      - `600초 이상`
      - `confirm_bullish=true`
      - `signal_score >= 90`
      - 이면 `fresh_cross` 없이도 재진입 허용
  - score 배분 로그 해석 수정
    - `allocation_reason_top` 을 최고 점수 항목이 아니라 최저 점수 항목 기준으로 변경
- 근거 로그:
  - `XRP/KRW`
    - `2026-04-09 04:18` `break_even_guard_take_profit`, `MFE 0.2973%`, `net -0.7934%`
    - `2026-04-10 18:30` `break_even_guard_take_profit`, `MFE 0.8724%`, `net -0.5232%`
  - 즉 XRP는 수익 구간이 있었는데도 보호 청산이 늦어 음수까지 반납한 뒤 정리되는 패턴이 확인됨
  - BTC 손절 후 구간에서는 `confirm=true`, 높은 `signal_score`가 자주 보였지만 `fresh_cross=false` 때문에 계속 막힘
  - `allocation_reason_top` 은 실제 병목보다 `execution`, `diversification` 같은 높은 점수 항목이 먼저 찍혀 설명성이 떨어졌음
- 현재 관찰:
  - `OKX BTC/USDT` 로그에는 `relaxed_fresh_cross=True` 가 실제로 찍히는 구간이 생김
  - 다만 동시에 `LOW_ENERGY` / `skip` 레짐이면 여전히 진입은 막히므로, 완화가 들어가도 무조건 재진입하진 않음
  - score 로그는 이제 “가장 약한 축” 기준으로 읽히게 되어 해석이 더 자연스러워짐
- 해석:
  - XRP는 손절폭보다 보호 청산 타이밍이 더 중요한 문제였고, 그래서 양수 바닥을 더 강하게 요구하는 쪽이 맞다고 판단
  - BTC는 fresh cross를 완전히 제거하는 것이 아니라, 충분히 강한 추세 재개 신호에만 예외를 주는 방식이 안전하다고 판단
  - score 기반 배분은 계산 자체보다 설명성이 중요하므로, 현재처럼 약점 축을 reason으로 남기는 방식이 더 실전적이라고 판단

### 35. Regime 가중 신호 점수 + Exit 강화 + 최근 7일 자동 튜닝 (2026-04-19)

- 변경 내용:
  - 신호 점수 고도화
    - [core/strategy/indicators.py](core/strategy/indicators.py)에 `calc_weighted_signal_score` 추가
    - 알트/ BTC 신호 점수는 이제 단순 고정 합산이 아니라 레짐별 가중치로 계산
    - 의도:
      - `TRENDING*` 에서는 slope / trend / spread 비중 확대
      - `CHOPPY*` 에서는 Bollinger squeeze / RSI 비중 확대
      - `BREAKOUT_ATTEMPT` 에서는 breakout / gap / volume 비중 확대
  - Exit 강화
    - 알트:
      - `Volume Spike Exit` 추가
      - 수익 구간에서 거래량 배수가 급감하면 `volume_spike_take_profit` 으로 조기 청산
    - BTC:
      - `ATR trailing exit` 추가
      - `Donchian breakout failure` 즉시 청산 추가
      - `donchian_failure_exit` reason 으로 분리
  - 코인별 자동 튜닝
    - [settings/strategy_settings.py](settings/strategy_settings.py)에서 최근 7일 final exit 기준 rolling 성과 분석
    - 사용 지표:
      - win-rate
      - profit-factor
    - 조정 대상:
      - `min_gap_pct`
      - `take_profit_pct`
      - `stop_loss_pct`
    - 조정 폭:
      - 최대 `±10%`
- 현재 기본 규칙:
  - 최근 7일 final exit 가 `min_trades=2` 이상일 때만 자동 튜닝 적용
  - `win_rate >= 0.60` and `profit_factor >= 1.30`
    - `adjustment = +0.10`
  - `win_rate <= 0.40` or `profit_factor <= 0.90`
    - `adjustment = -0.10`
  - 그 외:
    - `adjustment = 0.0`
- 조정 방향:
  - `min_gap_pct`: `base * (1 - adjustment)`
  - `take_profit_pct`: `base * (1 + adjustment)`
  - `stop_loss_pct`: `base * (1 + adjustment)`
- 근거:
  - 최근 며칠 실거래에서
    - 강한 추세 구간은 slope / breakout 성분이 실제 승패 구분력이 높았고
    - 횡보 구간은 squeeze / RSI 계열이 더 설명력이 높았음
  - 알트는 수익 구간에서 거래량 급감 후 빠르게 이익을 반납하는 경우가 있어 거래량 붕괴 기반 조기 청산이 필요하다고 판단
  - BTC는 `Donchian breakout` 성격의 진입 이후 실패 시 더 빠른 실패 인식이 필요했고, 기존 퍼센트 trailing 만으로는 늦는 구간이 있어 ATR trailing 을 추가
- 구현 범위:
  - [core/strategy/indicators.py](core/strategy/indicators.py)
  - [core/strategy/alt.py](core/strategy/alt.py)
  - [core/strategy/btc.py](core/strategy/btc.py)
  - [core/risk/alt_exit.py](core/risk/alt_exit.py)
  - [core/strategy/funnels.py](core/strategy/funnels.py)
  - [settings/strategy_settings.py](settings/strategy_settings.py)
  - [settings/btc_trend_settings.py](settings/btc_trend_settings.py)
  - 알트/ BTC 봇 4개 연결
- 검증:
  - `unittest discover -s tests -v` 통과
  - `py_compile` 통과
  - 거래 봇 4개 재기동 및 healthcheck 정상

### 36. Mean Reversion 라우팅 + 알트 ATR sizing + Sharpe 후보 랭킹 (2026-04-20)

- 변경 내용:
  - `mean_reversion` 전략 모듈 추가
    - [core/strategy/mean_reversion.py](core/strategy/mean_reversion.py)
    - Bollinger 하단 이탈 후 복귀와 중단 회귀 여지를 기준으로 진입 점수 계산
    - 기존 `signal_score_min`, RSI, MACD 필터 결과를 그대로 전달받아 우회하지 않도록 설계
  - 레짐 라우터 확장
    - [core/strategy/regime_router.py](core/strategy/regime_router.py)
    - `CHOPPY_LOW_VOL`, `CHOPPY_HIGH_VOL` 알트 경로를 `mean_reversion` 으로 전환
    - [settings/market_regime_guard.py](settings/market_regime_guard.py)
    - 알트 CHOPPY 정책은 mean reversion 이 실제로 작동하도록 신규 진입 일시정지를 완화
  - 알트 ATR position sizing 직접 연결
    - [settings/strategy_settings.py](settings/strategy_settings.py)
    - [ma_crossover_bot.py](ma_crossover_bot.py)
    - [upbit_ma_crossover_bot.py](upbit_ma_crossover_bot.py)
    - 알트 자체 `atr_pct` 로 포지션 비중 scale 을 직접 조정
  - Sharpe 기반 후보 랭킹
    - [tools/discover_untracked_symbols.py](tools/discover_untracked_symbols.py)
    - 최근 N일 일봉 수익률 평균 / 변동성 기반 Sharpe 유사 점수로 미등록 심볼 후보 정렬
    - 실거래 심볼 목록은 자동 변경하지 않고 discovery 출력만 제공
- 기본 설정:
  - `CHOPPY_LOW_VOL` 알트 레짐 포지션 스케일: `0.25`
  - 알트 ATR scale:
    - `<0.12%`: `1.10x`
    - `<0.20%`: `0.90x`
    - `<0.35%`: `0.65x`
    - 그 이상: `1.0x`
- Architect 검증:
  - `APPROVED WITH RISKS`
  - 잔여 리스크:
    - Sharpe 랭킹은 discovery 출력만 하며 live 심볼 자동 변경은 하지 않음
- 검증:
  - `unittest discover -s tests -v` 통과
  - `py_compile` 통과
  - OKX/업비트 알트 봇 재기동 및 healthcheck 정상

### 37. BTC 손절 억제용 확인 추세/거래량 보너스 보수화 (2026-04-23)

- 변경 내용:
  - BTC 최소 ATR 하한 상향
    - `BTC/USDT`: `0.14 -> 0.16`
    - `BTC/KRW`: `0.125 -> 0.14`
  - 확인 타임프레임 bullish 를 `종가 > 확인 EMA` 단독이 아니라 `확인 EMA slope 하한`까지 함께 충족할 때만 유효 처리
    - `BTC/USDT`: `confirm_ema_slope_pct >= 0.02`
    - `BTC/KRW`: `confirm_ema_slope_pct >= 0.015`
  - 거래량 보너스/동적 overweight 는 ATR 동반 시에만 허용
    - `volume_ratio >= 1.5` 구간 보너스는
      - `BTC/USDT`: `ATR >= 0.16%`
      - `BTC/KRW`: `ATR >= 0.14%`
    - `volume_ratio >= 3.0` 고거래량 추격 구간은 추가 ATR 하한 강화
      - `BTC/USDT`: `ATR >= 0.18%`
      - `BTC/KRW`: `ATR >= 0.16%`
- 근거 로그:
  - 최근 실거래 손절 분석에서 `confirm_bullish=True` 인 거래도 손절이 반복되어, 단순 상위 EMA 위 여부만으로는 보호력이 거의 없었음
  - `volume_ratio` 가 높은 손절 거래가 계속 확인되어, 거래량 증가를 단독 긍정 신호로 쓰는 해석이 추격 진입을 허용하는 쪽으로 작동했음
  - 반대로 수익 거래는 대체로 `ATR` 이 더 높고, 상위 slope 도 더 살아 있는 구간에서 발생했음
- 해석:
  - 손절 억제의 우선순위는 손절폭 확대가 아니라 `약한 상위 추세`와 `ATR 이 약한 거래량 급증`을 보너스 신호에서 제외하는 것
  - 즉 확인 추세는 더 좁게, 거래량 보너스는 더 늦게 인정하는 쪽이 현재 표본과 맞다고 판단
- 구현 범위:
  - [settings/btc_trend_settings.py](settings/btc_trend_settings.py)
  - [config/runtime.toml](config/runtime.toml)
  - [okx_btc_ema_trend_bot.py](okx_btc_ema_trend_bot.py)
  - [upbit_btc_ema_trend_bot.py](upbit_btc_ema_trend_bot.py)
  - [tests/test_btc_trend_settings.py](tests/test_btc_trend_settings.py)
- 검증:
  - `python -m unittest tests.test_btc_trend_settings -v`
  - `py_compile`
  - BTC 봇 재기동 및 healthcheck 확인

### 38. TradingAgents 참고형 의사결정 감사 레이어 도입 (2026-04-28)

- 변경 배경:
  - TradingAgents 는 LLM multi-agent 프레임워크로 analyst / researcher / trader / risk manager / portfolio manager 역할을 나눠 의사결정을 기록하고 검토한다.
  - 실거래 자동매매에서 LLM 이 직접 주문을 결정하는 방식은 비결정성과 지연이 커서 채택하지 않았다.
  - 대신 안전하게 흡수 가능한 decision log, risk review, reflection 개념을 기존 deterministic 전략 위에 감사 레이어로 적용했다.
- 변경 내용:
  - [core/risk/review.py](core/risk/review.py)
    - 체결 레코드의 `signal_score`, volume/volatility filter, HTF, PnL, MFE, 보유시간을 기반으로 `allow_candidate / reduce_candidate / block_candidate` 성격의 사후 risk review 를 생성
    - 주문 gate 를 직접 바꾸지 않고 체결 품질 분석과 다음 튜닝 후보 식별에 사용
  - [reporting/decision_journal.py](reporting/decision_journal.py)
    - 체결마다 `reports/decision_journal/YYYY-MM-DD/decision_journal.jsonl` 에 risk review 와 reflection 을 누적
    - journal 이 비어 있으면 최근 `trade_history` 에서 같은 review 를 임시 생성해 리포트 공백을 줄임
  - [trade_history_logger.py](trade_history_logger.py)
    - OKX/업비트, BTC/알트 공통 체결 로깅 경로에서 decision journal 을 함께 기록
  - [reporting/telegram_command_listener.py](reporting/telegram_command_listener.py)
    - `/analysis`, `/weekly` 에 최근 의사결정 리뷰와 reflection 요약을 추가
- 채택하지 않은 것:
  - LLM multi-agent 가 실시간 `buy/sell` 을 직접 결정하는 구조는 미채택
  - 뉴스/감성 분석 기반 즉시 주문 gate 도 미채택
- 기대 효과:
  - 체결 후 반복 손절 패턴을 `trade_history` 보다 더 직접적인 review 형태로 확인
  - 손절 거래의 공통 우려 항목을 텔레그램 리포트에서 바로 확인
  - 앞으로 튜닝 시 "왜 이 진입이 위험했는지" 를 기록 기반으로 재검토 가능
- 검증:
  - `python -m unittest tests.test_decision_journal -v`
  - `py_compile`
  - 텔레그램 리포트 문자열 생성 확인

### 39. 단독 지표 오탐 방지용 결합 필터 도입 (2026-05-01)

- 변경 배경:
  - 최근 7일 실거래 분석에서 `volume_ratio`, `signal_score`, `RSI/MACD`, `HTF bullish` 는 단독으로 손절을 충분히 구분하지 못했다.
  - 특히 BTC 손절 거래는 거래량과 신호가 강했지만 `ATR percentile 100`, `RSI 73`, range 상단 추격 성격이 겹쳤다.
- 변경 내용:
  - [core/strategy/combined_filters.py](core/strategy/combined_filters.py)
    - 최근 range 위치, 최근 고점/저점 거리 계산 helper 추가
    - `volume_ratio + ATR percentile + RSI` 가 동시에 과열이면 신규 진입 리스크로 판정
    - 신호가 강해도 range 상단 또는 최근 고점 근접이면 entry confirmation 을 추가 요구
  - [core/strategy/mean_reversion.py](core/strategy/mean_reversion.py)
    - mean reversion 완화 경로에 `ATR percentile <= 80`, `range position <= 35` 조건을 결합
    - RSI/MACD 완화가 고변동 추격 진입으로 변질되지 않게 제한
  - OKX/업비트 알트, OKX/업비트 BTC 봇
    - 고거래량+고ATR+RSI 과열 조합은 신규 진입 후보에서 제외
    - 강한 신호라도 최근 range 상단 추격이면 confirmation loop 를 1회 추가
  - [config/runtime.toml](config/runtime.toml)
    - 결합 필터 임계값을 canonical 설정으로 추가
- 현재 적용 기준:
  - `overheat_guard_volume_ratio = 2.0`
  - `overheat_guard_atr_percentile = 85.0`
  - `overheat_guard_rsi = 68.0`
  - `overheat_extra_confirmation_range_position_pct = 70.0`
  - `overheat_extra_confirmation_distance_from_high_pct = 0.20`
  - `overheat_extra_confirmation_loops = 1`
  - mean reversion 은 `mean_reversion_max_atr_percentile = 80.0`, `mean_reversion_max_range_position_pct = 35.0`
- 향후 플랜:
  - `signal_score` 는 ATR/RSI/range 위치가 과열일 때 점수 자체를 감점하는 방식으로 고도화
  - `correlation_with_btc` 는 BTC 레짐이 과열/손절 직후일 때만 알트 비중 축소에 더 강하게 반영
  - `orderbook_pressure_score` 는 진입 허용 조건이 아니라 체결 품질과 주문 비중 보정용으로만 사용
  - `HTF bullish` 는 필수 배경 조건으로 유지하되, range 상단 추격/ATR 과열과 충돌하면 추가 확인을 더 요구
  - 체결 로그의 `position_id` 를 알트까지 완전히 일관화해 진입 지표와 최종 청산을 더 정확히 연결
- 검증:
  - `tests/test_combined_filters.py`
  - `tests/test_mean_reversion.py`
  - 설정 로더 테스트에 결합 필터 설정값 확인 추가

### 40. 손절 방지 목표 결합 가드 1차 반영 (2026-05-02)

- 변경 배경:
  - 최근 손절 분석에서 단순 거래량 증가, 높은 신호 점수, HTF 상승 여부만으로는 손절을 충분히 막지 못했다.
  - 손절 방지에는 단독 지표보다 `BTC 상태`, `알트 변동성`, `체결/호가 우위`, `직전 손절 조건 반복 여부`를 함께 보는 쪽이 더 직접적이라고 판단했다.
- 변경 내용:
  - [core/strategy/combined_filters.py](core/strategy/combined_filters.py)
    - `BTC 위험 레짐 + BTC 상관계수 + 알트 ATR percentile` 조합 가드 추가
    - `거래량 급증 + 고ATR + 약한 체결비율/호가 압력` 조합 가드 추가
    - 손절 직후 이전 손절과 유사한 조건이면 재진입을 막는 context similarity 가드 추가
  - OKX/업비트 알트 봇
    - 세 조합이 켜지면 신규 진입 후보에서 제외
    - 구조화 로그와 entry funnel 에 `btc_regime_correlation_volatility_guard`, `volume_atr_execution_guard`, `stop_loss_context_reentry_guard` 단계 기록
    - 손절 체결 시점의 위험 context 를 런타임에 저장해 이후 재진입 조건과 비교
  - [config/runtime.toml](config/runtime.toml)
    - 손절 방지 결합 가드 임계값을 canonical 설정으로 추가
- 현재 적용 기준:
  - BTC 위험 레짐: `LOW_ENERGY, OVERHEATED, EXHAUSTION_RISK, CHOPPY_HIGH_VOL`
  - BTC 상관계수 기준: `0.75`
  - 알트 ATR percentile 기준: `70.0`
  - 거래량+체결 가드: `volume_ratio >= 2.0`, `ATR percentile >= 80.0`, `fill_ratio < 0.98` 또는 `orderbook_pressure_score < 45.0`
  - 손절 후 유사 조건 재진입 차단: `3600초` 안에 위험 context 3개 이상 일치
- 향후 플랜:
  - 손절 context 를 런타임 메모리뿐 아니라 trade history/decision journal 에도 저장해 재기동 후에도 비교 가능하게 확장
  - OKX/업비트 모두 실시간 호가 압력 값을 봇 루프에서 직접 읽도록 연결해 `orderbook_pressure_score` 공백을 줄임
  - 차단된 후보와 실제 이후 가격 흐름을 백테스트 리플레이에서 비교해 기준값을 심볼별로 분리

### 41. 손절 방지에 약한 단독 지표 가중치 축소 (2026-05-02)

- 변경 배경:
  - 최근 실거래와 `public_buy_ready` 후보 분석에서 `HTF bullish`, `signal_is_strong`, `volume_ratio`, `gap_pct`, `range_position_pct`, `correlation_with_btc` 는 단독으로 손절을 잘 구분하지 못했다.
  - 특히 BTC 손절은 `confirm_bullish=True` 와 매우 높은 `volume_ratio` 상태에서도 발생했고, 후보 로그에서는 `htf_bullish=True` 전체 후보 중 불리한 흐름이 절반 이상이었다.
- 변경 내용:
  - [core/strategy/alt.py](core/strategy/alt.py)
    - 알트 신호 점수에서 `volume` 과 `gap` 단독 가중치를 낮춤
    - `slope`, `MACD`, `RSI`, `squeeze` 같이 후속 탄력/회복을 설명하는 지표 비중을 상대적으로 높임
  - [core/risk/allocation.py](core/risk/allocation.py)
    - 거래량 단독 가산을 축소
    - `volume_ratio >= 2.0` 이면서 `ATR percentile >= 70`이면 allocation market score 감점
    - `orderbook_pressure_score < 50`이면 execution score 추가 감점
    - BTC 상관계수 단독 페널티를 완화하고, 위험 조합은 별도 결합 가드가 맡도록 분리
  - OKX/업비트 알트 봇
    - `correlation_with_btc` 단독 차단은 결합 손절방지 가드가 꺼진 경우의 fallback 으로만 사용
  - [config/runtime.toml](config/runtime.toml)
    - allocation score 가중치를 `signal 0.30 / market 0.30 / execution 0.25 / diversification 0.15` 로 조정
- 판단:
  - 단독 지표를 삭제하지는 않는다.
  - 다만 단독 긍정 신호로 매수 비중이 커지는 구조는 줄이고, 위험 조합일 때 차단/감점되도록 유지한다.

### 42. 변경 효과 자동 비교와 미체결 후보 가상 추적 (2026-05-06)

- 변경 배경:
  - 최근 전략 변경이 많아졌지만, 변경 직후 `진입이 더 막혔는지`, `손절이 줄었는지`, `막힌 후보가 실제로는 수익 기회였는지`를 한 번에 비교하는 루프가 부족했다.
  - 손절 방지 목표에서는 필터를 추가하는 것보다, 차단된 후보의 사후 가격 흐름을 계속 검증하는 장치가 먼저 필요하다고 판단했다.
- 변경 내용:
  - [reporting/change_effect_report.py](reporting/change_effect_report.py)
    - 최신 git 변경 시각 또는 지정 시각 기준으로 전후 `scan`, `ready`, `order_requested`, `filled`, 주요 차단 사유, 손절 수, 평균 순손익을 비교
    - CLI: `.venv/bin/python tools/change_effect_report.py --hours 12`
  - [reporting/shadow_candidate_tracker.py](reporting/shadow_candidate_tracker.py)
    - 실제 매수되지 않은 entry scan 후보를 이후 scan 가격으로 가상 추적
    - 후보별 `MFE`, `MAE`, 최종 수익률, 가상 TP/SL 도달 여부, 첫 차단 사유를 기록
    - CLI: `.venv/bin/python tools/shadow_candidate_tracker.py --hours 6 --horizon-minutes 60`
  - [reporting/telegram_command_listener.py](reporting/telegram_command_listener.py)
    - `/change`, `/shadow` 명령 추가
    - `/analysis` 에 변경 효과와 미체결 후보 요약을 함께 표시
- 운영 원칙:
  - 이 기능은 주문 gate 를 직접 바꾸지 않는다.
  - 먼저 차단된 후보의 사후 성과를 쌓고, 어떤 차단 사유가 실제 수익 기회를 과도하게 막는지 확인한 뒤 설정값을 조정한다.
- 검증:
  - `tests/test_change_effect_report.py`
  - `tests/test_shadow_candidate_tracker.py`

### 43. 텔레그램 리포트 판정 중심 정리 (2026-05-06)

- 변경 배경:
  - 텔레그램 리포트에 `아직 데이터가 없습니다`, `ready 0 / filled 0` 같은 저신호 문구가 반복되면 실제 판단에 방해가 된다.
  - 변경 효과와 미체결 후보 리포트는 숫자보다 `현재 조정이 개선인지, 표본 부족인지, 위험 신호인지`가 먼저 보여야 한다.
- 변경 내용:
  - [reporting/telegram_command_listener.py](reporting/telegram_command_listener.py)
    - `/analysis`, 일일 리포트, 주간 리포트에서 빈 보조 섹션을 자동 숨김
    - 전략 퍼널/병목/체결 변화 문구를 진입 기준으로 정리하고 ready율, 병목 비중을 함께 표시
    - 심볼별 결론은 원자료 나열보다 행동 판단 문구 중심으로 표시
  - [reporting/change_effect_report.py](reporting/change_effect_report.py)
    - 변경 전후 비교에 `판정` 문구와 시간당 scan 흐름을 추가
  - [reporting/shadow_candidate_tracker.py](reporting/shadow_candidate_tracker.py)
    - 미체결 후보 요약에 가상 익절/손절 비율 기반 판정 문구를 추가
- 운영 원칙:
  - 직접 명령(`/pnl`, `/last` 등)은 데이터 없음도 그대로 알려준다.
  - 복합 리포트(`/analysis`, 정기 리포트)는 판단에 필요한 섹션만 남겨 읽는 시간을 줄인다.

### 44. 자동복구 watchdog 과 매수 검토 위원회 shadow 도입 (2026-05-06)

- 변경 배경:
  - 장애가 반복될 때 운영자가 로그를 보고 수동 재기동하는 시간이 길면 실제 거래 기회와 로그 연속성이 함께 손상된다.
  - 매수 신호도 단일 점수만 보지 말고 전략/리스크/체결/포트폴리오/레짐 관점을 분리해, 어떤 관점이 반대했는지 기록할 필요가 있었다.
- 변경 내용:
  - [tools/auto_recovery_watchdog.py](tools/auto_recovery_watchdog.py)
    - [tools/healthcheck.py](tools/healthcheck.py) 결과에서 `FAIL` 또는 기본 설정상 `WARN` 프로그램을 감지
    - 쿨다운 `300초`, 시간당 최대 `3회` 제한을 둔 뒤 `bot_manager` 경로로 재기동
    - 복구 성공/실패/보류를 `logs/runtime/auto_recovery/events.jsonl` 과 `logs/YYYY-MM-DD/auto_recovery_watchdog.log` 에 기록
    - 복구 성공 시 텔레그램에 `장애 발생하여 해결완료` 형식으로 원인, 조치, 새 PID를 전송
  - [core/runtime/program_registry.py](core/runtime/program_registry.py)
    - `auto_recovery` 를 관리 대상 프로그램과 `start all` 순서에 추가
  - [core/strategy/entry_committee.py](core/strategy/entry_committee.py)
    - `strategy`, `risk`, `execution`, `portfolio`, `regime` 5개 관점으로 매수 후보를 독립 평가
    - 현재 [config/runtime.toml](config/runtime.toml)은 `mode = "shadow"` 로 두어 실제 진입을 추가 차단하지 않고 구조화 로그만 남김
    - 향후 표본이 쌓이면 `mode = "active"` 로 전환해 위원회 거절을 entry funnel 단계로 연결 가능
- 운영 원칙:
  - 자동복구는 프로세스 재기동까지만 수행하고, 코드 수정이나 설정 변경은 자동으로 하지 않는다.
  - 매수 검토 위원회는 먼저 shadow 로그로 거절 관점과 실제 이후 성과를 비교한 뒤 active 전환 여부를 판단한다.
- 검증:
  - `tests/test_auto_recovery_watchdog.py`
  - `tests/test_entry_committee.py`

### 47. ETH/KRW 한정 빠른 수익보호 적용 (2026-05-13)

- 변경 배경:
  - 90일 지표 민감도 백테스트에서 진입 필터 완화는 대부분 거래 수와 수익률을 바꾸지 못했다.
  - `profit_take_quicker` 세트는 `upbit ETH/KRW`에서만 수익률, PF, Sharpe, MDD가 함께 개선됐고 `upbit XRP/KRW`는 악화됐다.
- 변경 내용:
  - [config/runtime.toml](config/runtime.toml)
    - `ETH/KRW min_take_profit_pct: 0.75 -> 0.55`
    - `ETH/KRW fee_protect_min_net_pnl_pct: 0.06` 추가
  - [config/runtime.local.toml](config/runtime.local.toml)
    - 실제 운영 override 에 동일 값 반영
  - [config/sets/mixed.toml](config/sets/mixed.toml)
    - 세트 재적용 시에도 ETH/KRW 빠른 수익보호와 XRP 빠른익절 보류 기준이 유지되도록 정리
- 보류한 변경:
  - BTC ATR/거래량 완화는 OKX BTC 거래수만 늘리고 수익률을 악화시켜 미적용
  - XRP 빠른 익절 전역 적용은 `XRP/KRW` 악화가 확인되어 미적용
- 기대 효과:
  - ETH/KRW 수익 구간의 되돌림을 더 빨리 보호한다.
  - BTC와 XRP는 검증되지 않은 완화로 손실성 거래가 늘어나는 것을 막는다.
- 검증:
  - `reports/backtest_batches/20260513_indicator_sensitivity_90d/sensitivity_summary.md`

### 46. 포지션 비중 계산 공통화 리팩토링 (2026-05-07, runtime refactor)

- 변경 배경:
  - 최근 레짐, BTC 레짐, BTC ATR, ALT ATR, allocation score, probe 보정이 추가되면서 OKX/업비트 알트 봇과 OKX/업비트 BTC 봇에 같은 계산 순서가 반복됐다.
  - 전략값은 유지하되, 계산 순서가 거래소별로 갈라질 가능성을 줄여야 했다.
- 변경 내용:
  - [core/risk/allocation.py](core/risk/allocation.py)
    - `AltPositionSizingResult`, `BtcPositionSizingResult` 추가
    - `build_alt_position_sizing(...)`, `build_btc_position_sizing(...)` 추가
    - OKX/업비트가 같은 포지션 비중, allocation score, 포트폴리오 예산, 동적 보너스 로그 문구를 쓰도록 formatter 추가
  - [ma_crossover_bot.py](ma_crossover_bot.py), [upbit_ma_crossover_bot.py](upbit_ma_crossover_bot.py)
    - 알트 신규 진입 비중 계산을 공통 helper 로 대체
  - [okx_btc_ema_trend_bot.py](okx_btc_ema_trend_bot.py), [upbit_btc_ema_trend_bot.py](upbit_btc_ema_trend_bot.py)
    - BTC 신규 진입 비중 계산을 공통 helper 로 대체
  - [bot_manager.py](bot_manager.py)
    - 재기동 중 남은 defunct PID 를 실행 중인 봇으로 오판하지 않도록 `ps stat` 기반 pidfile 정리를 추가
- 해석:
  - 이번 변경은 전략 조정이 아니라 런타임 리팩토링이다.
  - 신규 진입 비중 계산 순서는 기존과 동일하게 유지했다.
  - 이후 레짐/ATR/score 기반 비중 조정은 `core/risk/allocation.py` 테스트를 먼저 갱신한 뒤 봇 본체에 연결한다.
- 검증:
  - `tests/test_regime_position_scale.py`
  - `tests/test_strategy_settings.py`
  - `tests/test_btc_trend_settings.py`
  - `tests/test_upbit_ma_crossover_bot.py`
  - `tests/test_upbit_provider.py`
  - `tests/test_bot_manager.py`
  - `python -m unittest discover -s tests -p 'test_*.py'`
  - `py_compile` 대상: 네 개 실거래 봇과 [core/risk/allocation.py](core/risk/allocation.py)

### 45. 장기 과거 시장 데이터 수집 기준 추가 (2026-05-06)

- 변경 배경:
  - 손절 방지 목표를 검증하려면 최근 며칠 체결 로그만으로는 표본이 부족하다.
  - BTC/ETH 는 여러 레짐을 포함해야 하므로 3년치가 필요하고, 알트는 상장/유동성 구조가 자주 바뀌므로 최근 1년 중심이 더 실용적이다.
- 변경 내용:
  - [tools/historical_market_collector.py](tools/historical_market_collector.py)
    - BTC/ETH 는 3년, 그 외 알트는 1년으로 자동 기간을 나누는 수집 도구 추가
    - `1m` OHLCV 를 백테스트 호환 JSONL 로 저장
    - OKX 는 spot 대응 SWAP `funding-rate-history` 도 함께 수집 가능
    - 중복 timestamp 는 건너뛰도록 구성해 중간 중단 후 같은 명령으로 이어받을 수 있게 함
    - 장시간 수집은 `launch/status` 로 백그라운드 실행과 PID 확인이 가능하게 함
    - `launch` 완료/실패 텔레그램 알림과 기존 PID 감시용 `launch-watch` 를 추가
  - [docs/HISTORICAL_MARKET_DATA.md](docs/HISTORICAL_MARKET_DATA.md)
    - 수집 대상, 저장 경로, OHLCV/funding 필드, 제한 사항 문서화
- 수집 필드:
  - 공통 OHLCV: `timestamp_ms`, `open`, `high`, `low`, `close`, `volume_base`, `quote_volume`
  - OKX 추가: `volCcy`, `volCcyQuote`, `confirm`
  - 업비트 추가: UTC/KST 캔들 시각, 누적 거래대금
  - OKX funding: `funding_rate`, `realized_rate`, `method`, `formula_type`
- 제한:
  - 과거 호가 스냅샷은 공개 API로 장기간 소급 수집하지 않고, 앞으로 누적되는 live snapshot 을 사용한다.
- 검증:
  - `tests/test_historical_market_collector.py`

## 앞으로 기록할 때 남기면 좋은 항목

- 수정 날짜
- 바꾼 파일 또는 `.env` 키
- 변경 전 값 / 변경 후 값
- 참고한 로그:
  - `structured_logs/live/*/strategy.jsonl`
  - `trade_logs/trade_history.jsonl`
  - `analysis_logs/*.jsonl`
  - `logs/*.log`
- 핵심 관찰:
  - 예: `no_bullish_signal 비중이 80% 이상`
  - 예: `익절 전에 손절이 반복`
  - 예: `distance_too_small 가 가장 큰 병목`
- 기대 효과:
  - 거래 수 증가
  - 수익 실현 속도 개선
  - 손절 감소

## 운영 원칙

- 값은 한 번에 과하게 바꾸지 않고, 한두 개씩만 조정합니다.
- 변경 후에는 반드시 로그가 충분히 쌓인 뒤 다시 평가합니다.
- 체결 수가 적을 때는 손익보다 `병목 reason`과 `ready -> filled` 흐름을 먼저 봅니다.
