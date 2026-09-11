# PROJECT.md

## 1. 프로젝트 개요
직원의 자기 평가 응답을 관리하고 부서 성과 및 개인 평가 점수를 반영하여 최종 평가 점수를 산출하는 웹 애플리케이션이다.

## 2. 사용자
### EMPLOYEE
- 이름/사번/비밀번호 로그인
- 본인 평가만 조회
- 문항 응답
- 임시 저장
- 진행률 확인
- 최종 제출

### ADMIN
- 사용자 CRUD/비활성화
- 부서 CRUD/비활성화
- 평가 기간 관리
- 평가 문항 및 가중치 관리
- 1차/2차 평가자 지정
- 응답 현황/미응답자 조회
- CSV 다운로드
- 부서 성과 점수 관리
- 개인/최종 점수 조회 및 계산

## 3. 인증 모델
Django `AbstractUser` 기반 Custom User Model:
`accounts.User`

직원과 관리자는 동일 User 테이블을 사용한다.

```text
accounts.User
 ├─ role=EMPLOYEE
 └─ role=ADMIN
```

`AUTH_USER_MODEL = "accounts.User"`

## 4. 핵심 개념
- Department
- ReviewPeriod
- Question
- Choice
- Review
- Answer
- DepartmentPerformance
- FinalScore

## 5. 평가 생명주기
```text
ReviewPeriod: DRAFT → OPEN → CLOSED
Review: NOT_STARTED → IN_PROGRESS → SUBMITTED
```

동일 직원 + 동일 평가 기간에는 Review 하나만 존재한다.

## 6. 점수
문항 가중치 합계는 기본적으로 100.
개인 점수는 0~100.
부서 성과 점수는 0~100.
최종 점수는 0~100으로 clamp한다.

기본 예시:
`department_adjustment = (department_score - 70) * 0.20`
`final_score = clamp(individual_score + department_adjustment, 0, 100)`

위 조정식은 MVP 기본 정책이며 실제 운영 전 회사 정책 확인이 필요하다.

## 7. 프로젝트 구조
```text
performance-review/
├── backend/
│   ├── manage.py
│   ├── config/
│   ├── accounts/
│   ├── departments/
│   ├── reviews/
│   ├── scoring/
│   └── monitoring/
├── frontend/
│   ├── src/
│   └── ...
├── specs/
└── AGENTS.md
```
