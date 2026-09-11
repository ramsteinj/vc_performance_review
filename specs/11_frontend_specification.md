# 11. Frontend 명세

## 기술
- Vue.js 3
- Vite
- Bootstrap 5
- Vue Router
- Axios
- HTML5/CSS3

## Route
### 공통
- `/login`

### Employee
- `/`
- `/review`

### Admin
- `/admin`
- `/admin/users`
- `/admin/departments`
- `/admin/review-periods`
- `/admin/questions`
- `/admin/evaluators`
- `/admin/monitoring`
- `/admin/scores`

## 인증
로그인 후 `/auth/me/`에서 현재 User 정보를 확인한다.

Frontend role:
```text
EMPLOYEE
ADMIN
```

단, role 체크는 UI/라우팅 목적이며 실제 API 권한은 Backend가 결정한다.

## Employee UI
- 평가 진행률
- 문항
- 저장 상태
- 제출 버튼
- 제출 완료 상태

## Admin UI
Bootstrap 기반의 단순한 CRUD/table/form UI를 우선한다.

## API
Axios를 사용한다.
loading / empty / success / error 상태를 명확하게 처리한다.
