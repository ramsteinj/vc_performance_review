# 12. Backend 아키텍처

## Django Apps
권장:
```text
accounts
departments
reviews
scoring
monitoring
```

## Accounts
Custom User:
```text
accounts.User(AbstractUser)
```

설정:
```python
AUTH_USER_MODEL = "accounts.User"
```

절대:
```python
from django.contrib.auth.models import User
```
를 사용하지 않는다.

대신:
```python
from django.conf import settings
```
또는:
```python
from django.contrib.auth import get_user_model
```

## 계층
```text
DRF View
  ↓
Serializer
  ↓
Service / Domain Logic
  ↓
Django ORM
  ↓
PostgreSQL
```

## Service
다음 로직은 service로 분리한다.
- Review 생성
- Answer 저장
- Review 제출
- evaluator assignment
- score calculation
- CSV generation

## Transaction
Review 제출, 중복 방지가 필요한 여러 DB 변경에는 `transaction.atomic()`을 사용한다.

## ORM
N+1 방지를 위해 `select_related`, `prefetch_related`를 사용한다.

## 보안
- request.user 기반 접근
- role permission
- object-level authorization
- submitted review 수정 차단
- DB constraints
- 환경변수 secrets

## Custom User 주의사항
Custom User Model은 프로젝트 초기에 설정한다.
초기 migration 이후 User 모델을 교체하는 것은 복잡하므로 최초 migration 전에 확정한다.
