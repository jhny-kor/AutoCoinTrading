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
