# 13. 테스트

## Accounts
- employee_number unique
- password hashing
- inactive user login blocked
- EMPLOYEE/ADMIN role
- name + employee_number + password authentication

## Authorization
- Employee cannot access another employee Review
- Employee cannot call Admin APIs
- Admin can access Admin APIs
- client-provided user_id cannot bypass ownership
- submitted Review cannot be edited

## Review
- same employee + review period cannot create duplicate Review
- status transitions
- OPEN/CLOSED rules
- required answer validation

## Answer
- same review + question cannot duplicate
- upsert/draft save
- selected choice validation

## Scoring
- weighted average
- scale normalization
- department adjustment
- final score 0~100 clamp
- missing/invalid score handling

## DepartmentPerformance
- unique review period + department
- score 0~100 validation

## CSV
- Korean Excel compatibility
- correct headers
- correct user/department/score mapping

## Django Custom User
반드시 migration 및 ORM 관계 테스트를 포함한다.
다른 앱의 FK가 `settings.AUTH_USER_MODEL`을 사용하는지 확인한다.
