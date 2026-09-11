# 04. 평가 기간

## 상태
- DRAFT: 설정 중
- OPEN: 직원 응답 가능
- CLOSED: 종료

## 규칙
- OPEN 이전에는 직원이 응답할 수 없다.
- CLOSED 후에는 직원이 수정/제출할 수 없다.
- 평가 기간별 Question을 관리한다.
- OPEN 후에는 문항/가중치 변경을 제한한다.
- 같은 employee와 review_period 조합의 Review는 하나만 허용한다.

## 관리자 기능
- 생성
- 수정
- 상태 변경
- 조회
- 종료

## 자동 Review 생성
MVP에서는 OPEN 시 대상 직원의 Review를 생성하거나 최초 접근 시 생성할 수 있다.
어느 방식을 선택하든 `UniqueConstraint`로 중복 생성을 방지한다.
