# 실행 체크리스트

현재 canonical 문서입니다.

상세 내용

- [EXECUTION_CHECKLIST_2026-04-03.md](/Users/plo/Documents/auto_coin_bot/docs/EXECUTION_CHECKLIST_2026-04-03.md)

현재 운영 우선순위는 위 문서의 `P0 / P1 / P2` 태그를 기준으로 봅니다.

## 설정 시스템 후속 개선 메모

env/config 리팩토링 자체는 완료된 상태로 봅니다.

다만 추후 다시 볼 후속 개선 항목은 아래입니다.

- `typed config accessor` 적용 범위를 실행/리포트/도구 전역으로 더 넓히기
- `config/runtime.local.toml` 운용 규칙을 더 명확히 문서화하기
- `env_overrides` 를 history 전용 경로로 더 명확히 정리하기
- 설정 스키마 검증이나 시작 시 config sanity check 추가 검토
- 시장 구조 / 미시구조 shadow mode 도입 시 새 canonical config 체계에 맞춰 키 설계 재점검

즉 현재는 `설정 시스템 전환 완료`, 위 항목들은 `다음 단계 개선`으로 취급합니다.
