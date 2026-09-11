# 15. Acceptance Criteria

## Employee
- [ ] 이름/사번/비밀번호 로그인 가능
- [ ] inactive user 로그인 차단
- [ ] 본인 평가만 조회 가능
- [ ] 문항 응답 가능
- [ ] 임시 저장 가능
- [ ] 진행률 표시
- [ ] 필수 문항 미응답 제출 차단
- [ ] 제출 후 수정 차단
- [ ] 중복 Review 생성 차단

## Admin
- [ ] 사용자 CRUD/비활성화
- [ ] 부서 CRUD/비활성화
- [ ] 평가기간 CRUD/상태관리
- [ ] 문항 CRUD
- [ ] 문항 가중치 설정
- [ ] 1차 평가자 지정
- [ ] 2차 평가자 optional 지정
- [ ] 응답 현황
- [ ] 미응답자 조회
- [ ] CSV 다운로드
- [ ] 부서 성과 점수 입력/조회
- [ ] 개인 점수 계산
- [ ] 부서 조정점수 계산
- [ ] 최종 점수 0~100

## Custom User
- [ ] `accounts.User`가 `AbstractUser`를 상속
- [ ] `AUTH_USER_MODEL = "accounts.User"`
- [ ] Employee/Admin 별도 User 테이블 없음
- [ ] `role`로 EMPLOYEE/ADMIN 구분
- [ ] employee_number unique
- [ ] password Django hashing
- [ ] 다른 모델이 `settings.AUTH_USER_MODEL`을 참조
- [ ] `django.contrib.auth.models.User` 직접 참조 없음

## Security
- [ ] Backend authorization
- [ ] IDOR 방지
- [ ] client role/user_id 신뢰 금지
- [ ] Admin API 보호
- [ ] submitted review 수정 차단

## Data Integrity
- [ ] Review(review_period, employee) unique
- [ ] Answer(review, question) unique
- [ ] DepartmentPerformance(review_period, department) unique
- [ ] FinalScore.review unique
