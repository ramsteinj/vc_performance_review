# 03. 데이터 모델

## 1. 핵심 원칙
별도의 Employee/Admin 테이블을 만들지 않는다.
Django `AbstractUser` 기반 Custom User Model인 `accounts.User` 하나를 사용한다.

## 2. User
```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        ADMIN = "ADMIN", "Admin"

    employee_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=Role.choices,
                            default=Role.EMPLOYEE)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="users",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

`AbstractUser`의 `password`, `is_staff`, `is_superuser`, `last_login`, `date_joined` 등을 그대로 활용한다.

`AUTH_USER_MODEL = "accounts.User"`

## 3. Department
- name unique
- description
- is_active
- timestamps

User.department는 Department FK이며 `PROTECT`.

## 4. ReviewPeriod
- name
- description
- start_date
- end_date
- status: DRAFT/OPEN/CLOSED
- timestamps

## 5. Question
- review_period FK
- text
- description
- question_type: TEXT/SINGLE_CHOICE/MULTIPLE_CHOICE/SCALE
- weight
- display_order
- required
- is_active
- timestamps

활성 문항의 weight 합계는 기본적으로 100.

## 6. Choice
- question FK
- text
- display_order
- optional score

## 7. Review
- review_period FK
- employee → User
- primary_evaluator → User
- secondary_evaluator → User nullable
- status: NOT_STARTED/IN_PROGRESS/SUBMITTED
- submitted_at
- timestamps

DB:
`UniqueConstraint(review_period, employee)`

## 8. Answer
- review FK
- question FK
- answer_text
- score nullable
- selected_choices ManyToMany
- timestamps

DB:
`UniqueConstraint(review, question)`

## 9. DepartmentPerformance
- review_period FK
- department FK
- performance_score 0~100
- timestamps

DB:
`UniqueConstraint(review_period, department)`

## 10. FinalScore
- review OneToOne
- individual_score
- department_score
- department_adjustment
- final_score
- calculated_at

## 11. 관계
```text
Department 1 ─ N User
ReviewPeriod 1 ─ N Question
Question 1 ─ N Choice
ReviewPeriod 1 ─ N Review
Review 1 ─ N Answer
Review ─ User(employee/evaluators)
ReviewPeriod + Department 1 ─ 1 DepartmentPerformance
Review 1 ─ 1 FinalScore
```

## 12. 삭제 정책
User/Department/Question은 가능한 한 soft delete(`is_active=False`)를 사용한다.
평가 결과 데이터는 보존한다.

## 13. User 참조 규칙
모델:
```python
from django.conf import settings
employee = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
```

Python:
```python
from django.contrib.auth import get_user_model
User = get_user_model()
```

`django.contrib.auth.models.User`를 직접 import하지 않는다.
