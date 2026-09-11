# AGENTS.md

## 프로젝트 목적
Performance Review 시스템을 OpenCode + GLM-5.3 Flash 기반 Vibe Coding 방식으로 개발한다.

## 기술 스택
- Frontend: Vue.js 3, Vite, Bootstrap 5, HTML5, CSS3, SPA
- Backend: Python 3, Django, Django REST Framework, Django ORM
- Database: PostgreSQL

## 핵심 설계 원칙
1. Django `AbstractUser`를 상속한 Custom User Model을 사용한다.
2. 일반 직원과 관리자를 별도 User/Employee/Admin 테이블로 만들지 않는다.
3. `accounts.User`의 `role` 필드로 `EMPLOYEE` / `ADMIN`을 구분한다.
4. 프로젝트 시작부터 `AUTH_USER_MODEL = "accounts.User"`를 사용한다.
5. 다른 모델에서 User를 직접 참조할 때 `settings.AUTH_USER_MODEL`, 코드에서는 `get_user_model()`을 우선 사용한다.
6. 비밀번호는 Django password hashing을 사용한다.
7. 권한 검사는 반드시 Backend/DRF에서 수행한다.
8. Frontend의 role 체크는 UX 용도일 뿐 보안 경계가 아니다.
9. Review/Answer 등 중복 방지는 DB UniqueConstraint와 Backend validation을 함께 사용한다.
10. 복잡한 업무 로직은 View가 아니라 Service/Domain Logic에 둔다.
11. 과도한 라이브러리와 복잡한 아키텍처를 도입하지 않는다.
12. 기존 동작을 깨뜨리는 변경은 피하고 필요한 범위만 구현한다.

## Custom User 핵심
```python
class User(AbstractUser):
    employee_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=Role.choices)
    department = models.ForeignKey(..., null=True, blank=True)
```

- `role=EMPLOYEE`: 일반 직원
- `role=ADMIN`: 평가 관리자
- `is_staff`, `is_superuser`는 Django Admin 권한이며 애플리케이션 role과 동일하지 않다.
- 로그인 식별자는 `employee_number`; 이름은 추가 검증값으로 사용한다.

## Vibe Coding 규칙
복잡한 작업 전:
1. 관련 spec 확인
2. 현재 코드 구조 확인
3. 구현 계획 제시
4. 작은 단위로 구현
5. 테스트 실행
6. 변경 사항 요약

전체 애플리케이션을 한 번에 생성하지 않는다.

## 권장 구현 순서
1. Custom User
2. Department
3. ReviewPeriod
4. Question/Choice
5. Review/Answer
6. 인증/권한
7. 평가자 지정
8. 모니터링
9. 점수 계산
10. CSV
11. Frontend
12. 통합/보안 테스트
