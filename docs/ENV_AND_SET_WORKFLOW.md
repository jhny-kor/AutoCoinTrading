# .env / 전략 세트 파일 구조 한 페이지 정리

## 핵심 결론

현재 구조에서 **실제 운영 기준 파일은 `.env`** 입니다.

`env_overrides/*.env` 는 `.env` 를 대체하는 파일이 아니라,
**일부 키만 덮어쓰는 partial 전략 세트 파일** 입니다.

즉 현재는 아래 관계입니다.

- `.env` = 운영 본체
- `env_overrides/*.env` = 비교/튜닝용 부분 세트
- `tools/apply_strategy_set.py` = 부분 세트를 `.env` 에 반영하는 도구

---

## 1. `.env` 는 무엇인가

`.env` 는 현재 봇이 실제로 읽는 메인 설정 파일입니다.

여기에는 아래가 함께 들어 있습니다.

- 거래소 API 키
- 텔레그램 설정
- 최소 주문 금액
- 전략 공통값
- 심볼별 `*_MAP`
- 리스크 관리 설정
- 포트폴리오 배분 설정

즉 현재 운영에서는 `.env` 안에 **전체 설정이 다 있습니다.**

---

## 2. `env_overrides/*.env` 는 무엇인가

`env_overrides/*.env` 는 전체 설정 파일이 아닙니다.

이 파일들은 아래처럼 **일부 키만 담은 partial env** 입니다.

예:

- `env_overrides/conservative.env`
- `env_overrides/medium.env`
- `env_overrides/mixed.env`

이런 파일에는 보통 이런 값만 들어 있습니다.

- `STRATEGY_FEE_PROTECT_MIN_NET_PNL_PCT`
- `STRATEGY_MIN_TAKE_PROFIT_PCT_MAP`
- `STRATEGY_BREAK_EVEN_GUARD_MIN_MFE_PCT_MAP`
- `STRATEGY_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT_MAP`

즉 “세트별로 바뀌는 전략 키만 모아둔 패치 파일”입니다.

---

## 3. 실제 적용은 어떻게 되나

현재 봇은 `env_overrides/*.env` 를 직접 읽지 않습니다.

실제 적용 순서는 아래입니다.

1. `env_overrides/*.env` 에 세트 정의
2. `tools/apply_strategy_set.py` 실행
3. 이 도구가 partial env 안의 키만 현재 `.env` 에 덮어씀
4. 봇 재시작
5. 재시작 후 봇은 갱신된 `.env` 를 읽음

즉 실제 런타임 기준은 항상 `.env` 입니다.

---

## 4. 예시

예를 들어 혼합형 세트를 적용할 때는:

```bash
.venv/bin/python tools/apply_strategy_set.py --set mixed
```

이 명령은 내부적으로

- `env_overrides/mixed.env`

를 읽고,

- 그 안에 들어 있는 키만 `.env` 에 반영합니다.

반영 후에는 알트 봇 재시작이 필요합니다.

```bash
.venv/bin/python bot_manager.py stop okx
.venv/bin/python bot_manager.py stop upbit
.venv/bin/python bot_manager.py start okx
.venv/bin/python bot_manager.py start upbit
```

---

## 5. 왜 이렇게 쓰는가

장점은 아래와 같습니다.

- `.env` 전체를 복붙하지 않아도 됨
- 세트별 차이만 따로 관리 가능
- 비교 실험이 쉬움
- 실수로 API 키/운영 설정을 덮어쓸 위험이 줄어듦

즉 현재 구조는

- 운영 메인 파일은 하나로 유지하고
- 전략 세트만 부분 패치 형태로 교체

하는 방식입니다.

---

## 6. 지금 단계에서의 역할 분담

### `.env`

- 운영 메인 설정 파일
- 실제 봇이 읽는 파일

### `env_overrides/*.env`

- 전략 비교 세트 파일
- 일부 키만 포함
- 실험/튜닝용

### `tools/apply_strategy_set.py`

- partial env 를 `.env` 에 반영
- dry-run 으로 변경 키 미리보기 가능

### `reports/backtest_batches/...`

- 실제 비교 결과 저장
- 날짜/시각이 붙은 실험 결과물

### `reports/backtest_registry.json`

- 결과물 인덱스
- 최근 기준선과 diff 를 한 파일에서 추적

---

## 7. canonical 구조로 가면 어떻게 바뀌나

현재는 `.env` 가 메인입니다.

장기적으로 canonical 구조로 가면 보통 두 방향 중 하나입니다.

### 방향 A. 현재 방식 유지

- `.env` = 메인
- `env_overrides/*.env` = partial 세트

가장 실용적이고 현재 구조와 잘 맞습니다.

### 방향 B. 전략 설정과 비밀정보 분리

- `.env` = API 키, 텔레그램, 운영 비밀정보
- `config/sets/*.env` = 전략 설정 전용 canonical 파일

이 방식은 더 깔끔하지만, 지금은 리팩터링 비용이 큽니다.

현재 저장소는 **방향 A** 입니다.

---

## 8. 한 줄 요약

현재 구조에서

- `.env` 는 여전히 전체 운영 설정이 들어 있는 메인 파일이고
- `env_overrides/*.env` 는 `.env` 를 대체하는 파일이 아니라
- **일부 키만 덮어쓰는 전략 세트 파일** 입니다.
