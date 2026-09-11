# 02. 인증 및 권한

## Custom User Model
Django `AbstractUser`를 상속한다.

```python
class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        ADMIN = "ADMIN", "Admin"

    employee_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=Role.choices)
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )
```

`settings.py`:
```python
AUTH_USER_MODEL = "accounts.User"
```

## 로그인
입력:
- name
- employee_number
- password

`employee_number`로 User를 조회하고 name과 password를 검증한다.
비활성 사용자는 로그인할 수 없다.

권장 API:
`POST /api/auth/login/`
`POST /api/auth/logout/`
`GET /api/auth/me/`

## 권한
### Employee
- 자신의 Review만 접근
- 자신의 Answer만 생성/수정
- SUBMITTED Review 수정 금지

### Admin
- 사용자/부서/평가기간/문항/평가자/모니터링/점수 관리

## 보안 원칙
- client가 보내는 user_id/employee_id/role을 신뢰하지 않는다.
- 인증된 사용자 정보는 `request.user`에서 가져온다.
- IDOR를 방지한다.
- Admin API는 DRF permission으로 보호한다.
- Frontend route guard만으로 보안을 구현하지 않는다.
