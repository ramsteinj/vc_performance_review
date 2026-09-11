# 14. Vibe Coding Workflow

## 원칙
OpenCode + GLM-5.3 Flash에 전체 앱을 한 번에 만들도록 요청하지 않는다.

## Phase
1. spec review
2. architecture
3. Custom User + migration
4. Department
5. ReviewPeriod
6. Question/Choice
7. Review/Answer
8. authentication/authorization
9. evaluator assignment
10. employee review
11. monitoring
12. scoring
13. CSV
14. frontend
15. integration/security test

## Phase 1 prompt 예
```text
먼저 AGENTS.md와 PROJECT.md, specs/*.md를 읽어라.
현재 프로젝트에서 구현해야 할 범위를 분석하고,
Custom User(AbstractUser) 구조와 앱별 책임을 포함한 구현 계획을 작성하라.
아직 코드를 수정하지 마라.
```

## Custom User 구현 prompt
```text
03_data_model.md와 02_authentication_authorization.md를 기준으로
accounts.User를 Django AbstractUser 상속 방식으로 구현하라.
Employee/Admin 별도 모델을 만들지 말고 role 필드로 구분하라.
AUTH_USER_MODEL을 설정하고 migration/test까지 수행하라.
기존 Django User import가 있다면 모두 Custom User 방식으로 수정하라.
```

## 구현 후
```text
변경 파일, 핵심 구현 내용, 실행한 테스트, 남은 위험을 요약하라.
```

## 원칙
작은 변경 → 테스트 → 다음 단계.
