# 07. 직원 평가 응답

## 흐름
```text
NOT_STARTED
   ↓
IN_PROGRESS
   ↓
SUBMITTED
```

## 기능
- 현재 평가 기간 조회
- 질문 목록 조회
- 답변 작성
- 임시 저장
- 진행률
- 제출

## 임시 저장
각 문항 Answer를 upsert한다.
`(review, question)` unique constraint를 사용한다.

## 진행률
```text
answered_required_questions / total_required_questions * 100
```

## 제출
Backend에서 다음을 검증한다.
1. Review가 현재 로그인 사용자의 것인가?
2. ReviewPeriod가 OPEN인가?
3. 필수 문항이 모두 답변되었는가?
4. 이미 SUBMITTED 상태가 아닌가?

검증 성공 시 transaction 안에서 SUBMITTED 처리.

## 제출 후
- 직원 수정 금지
- 재제출 금지
- 관리자의 수정 권한은 별도 정책으로 결정

## 접근 제어
직원은 URL의 review_id를 바꿔 다른 직원 Review에 접근할 수 없어야 한다.
