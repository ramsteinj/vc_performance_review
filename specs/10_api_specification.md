# 10. API 명세

Base: `/api`

## 인증
- POST `/auth/login/`
- POST `/auth/logout/`
- GET `/auth/me/`

Login:
```json
{
  "name": "홍길동",
  "employee_number": "EMP001",
  "password": "password"
}
```

## Employee
- GET `/reviews/my/`
- GET `/reviews/{id}/`
- PUT/PATCH `/reviews/{id}/answers/`
- POST `/reviews/{id}/submit/`

Backend는 항상 `request.user`를 기준으로 본인 Review를 검증한다.

## Admin
- CRUD `/admin/users/`
- CRUD `/admin/departments/`
- CRUD `/admin/review-periods/`
- CRUD `/admin/questions/`
- evaluator assignment API
- monitoring API
- score API
- CSV export API

## User API
응답에는 필요 정보만 제공한다.
예:
```json
{
  "id": 1,
  "employee_number": "EMP001",
  "name": "홍길동",
  "role": "EMPLOYEE",
  "department": {
    "id": 2,
    "name": "개발팀"
  }
}
```

password, password hash 등 민감 정보는 API로 반환하지 않는다.

## 권한
DRF Permission:
- IsAuthenticated
- IsAdminUserRole
- IsEmployeeOwner

`is_staff`만으로 애플리케이션 ADMIN role을 대체하지 않는다.
