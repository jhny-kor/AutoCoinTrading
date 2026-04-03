# .env / 전략 세트 파일 구조 한 페이지 정리

## 핵심 결론

현재 구조에서 **실제 운영 기준 파일은 `.env.settings` + `.env.secrets`** 입니다.

`env_overrides/*.env` 는 이 메인 설정 파일을 대체하는 파일이 아니라,
**일부 전략 키만 덮어쓰는 partial 세트 파일** 입니다.

즉 현재 관계는 아래와 같습니다.

- `.env.settings` = 운영 설정 본체
- `.env.secrets` = 비밀정보 본체
- `.env.local` = 로컬 오버라이드
- `.env` = legacy fallback
- `env_overrides/*.env` = 비교/튜닝용 partial 전략 세트
- `tools/apply_strategy_set.py` = partial 세트를 `.env.settings` 에 반영하는 도구

---

## 1. 현재 실제로 읽는 파일

현재 중앙 로더는 아래 순서로 환경 파일을 읽습니다.

1. `.env.settings`
2. `.env.secrets`
3. `.env.local`
4. `.env` (split env 가 없을 때만 fallback)

즉 split env 가 있으면 `.env` 가 아니라 `.env.settings` + `.env.secrets` 가 실제 기준입니다.

---

## 2. 각 파일 역할

### `.env.settings`

- 운영 메인 설정 파일
- 전략 설정
- 리스크 설정
- 포트폴리오 설정
- 텔레그램 일반 설정
- 최소 주문 금액, 타임프레임, 맵 기반 전략값

### `.env.secrets`

- 비밀정보 파일
- 거래소 API 키
- 텔레그램 Bot 토큰
- 텔레그램 chat id

### `.env.local`

- 로컬 환경 전용 오버라이드
- 개인 장비에서만 잠깐 바꿔볼 값

### `.env`

- legacy fallback
- 예전 방식과 호환성 유지를 위한 파일
- split env 가 없는 환경에서만 기준 역할

### `env_overrides/*.env`

- 비교/튜닝용 partial env
- 일부 전략 키만 포함
- 전체 설정 파일이 아님

예:

- `env_overrides/conservative.env`
- `env_overrides/medium.env`
- `env_overrides/mixed.env`

### `env_overrides/history/*`

- 과거 세트 이력 보관
- 날짜 붙은 기준선 파일

---

## 3. 실제 적용 흐름

현재 세트 적용 순서는 아래입니다.

1. `env_overrides/*.env` 에 세트 정의
2. `tools/apply_strategy_set.py` 실행
3. partial env 안의 키만 `.env.settings` 에 덮어씀
4. 봇 재시작
5. 재시작 후 봇은 `.env.settings` + `.env.secrets` 를 읽음

즉 전략 세트 변경은 이제 `.env` 가 아니라 `.env.settings` 기준으로 반영됩니다.

---

## 4. 사용 예시

혼합형 세트 적용:

```bash
.venv/bin/python tools/apply_strategy_set.py --set mixed
```

미리보기:

```bash
.venv/bin/python tools/apply_strategy_set.py --set mixed --dry-run
```

반영 후 알트 봇 재시작:

```bash
.venv/bin/python bot_manager.py stop okx
.venv/bin/python bot_manager.py stop upbit
.venv/bin/python bot_manager.py start okx
.venv/bin/python bot_manager.py start upbit
```

---

## 5. 왜 이렇게 분리했나

장점

- API 키와 일반 설정을 분리할 수 있음
- 전략 세트 비교가 쉬워짐
- `.env.settings` 만 교체해 실험 가능
- 실수로 비밀정보까지 같이 덮어쓸 위험이 줄어듦
- 앞으로 설정 시스템을 더 키워도 구조를 유지하기 쉬움

---

## 6. 지금 단계의 의미

현재는 “대형 설정 시스템 리팩터링 1차” 상태입니다.

완료된 것

- split env 도입
- 중앙 로더 도입
- 핵심 설정/실행 모듈을 중앙 로더로 전환
- canonical 세트 파일 정리

아직 남은 것

- 실행 중인 모든 코드/문서가 split env 기준으로 완전히 맞는지 세부 점검
- `.env` fallback 을 장기적으로 유지할지 제거할지 결정
- 설정 레이어를 더 구조화된 파일 시스템으로 승격할지 검토

---

## 7. 한 줄 요약

현재 구조에서

- `.env.settings` + `.env.secrets` 가 실제 운영 기준 파일이고
- `.env` 는 legacy fallback 이며
- `env_overrides/*.env` 는 `.env.settings` 를 대체하는 파일이 아니라
- **일부 전략 키만 덮어쓰는 partial 세트 파일** 입니다.
