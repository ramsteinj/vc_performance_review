# 인사평가 (Performance Review) 시스템

직원 자기평가 응답을 수집·관리하고, 부서 성과 및 개인 평가 점수를 반영해 최종 평가 점수를 산출하는 웹 애플리케이션입니다.

요구사항 명세는 `PROJECT.md`와 `specs/01~15`에 정의되어 있으며, 에이전트/협업 규칙은 `AGENTS.md`를 참고하세요.

## 기술 스택

| 구분 | 기술 |
|---|---|
| Frontend | Vue 3, Vite 5, Bootstrap 5, Vue Router 4, Axios |
| Backend | Python 3.13, Django, Django REST Framework (Session 인증) |
| Database | PostgreSQL |

## 프로젝트 구조

```text
├── backend/            # Django 프로젝트 (manage.py 위치)
│   ├── config/         # settings / urls
│   ├── accounts/       # Custom User(EMPLOYEE/ADMIN role), 인증 API
│   ├── departments/    # 부서
│   ├── reviews/        # 평가 기간, 문항, 평가, 답변, 평가자 지정, 직원 평가 API
│   ├── scoring/        # 부서 성과 점수, 최종 점수 계산
│   └── monitoring/     # 응답 현황 통계, CSV export
├── frontend/           # Vue 3 SPA (Vite)
└── specs/              # 요구사항 명세 (01~15)
```

## 개발 환경 실행

사전 요구사항: Python 3.13, Node 18+, PostgreSQL (로컬 설치, 표준 포트 5432)

```bash
# 1) 개발용 PostgreSQL — 로컬에 설치된 인스턴스(5432)를 사용합니다 (Docker 불필요)
#    아래 롤/DB가 없다면 먼저 생성:
sudo -u postgres psql -c "CREATE ROLE perfreview LOGIN PASSWORD 'devpass';"
sudo -u postgres createdb -O perfreview perfreview

# 2) 백엔드 (저장소 루트에서)
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver          # http://localhost:8000

# 3) 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev                         # http://localhost:5173 (/api → 8000 프록시)
```

DB 연결 정보는 환경변수로 변경 가능합니다. 기본값은 위 로컬 PostgreSQL 설정과 일치합니다
(`backend/.env.example` 참고: `POSTGRES_*`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`).

### 기본 관리자 계정

백엔드 시작(`runserver`) 시 `ADM001` 계정이 없으면 자동 생성됩니다. 이미 존재하면 아무 것도 변경하지 않습니다.

로그인은 **이름 + 사번 + 비밀번호** 3가지입니다 (프론트엔드 `/login`).
기본 관리자 계정의 로그인 정보:

| 이름 | 사번 | 비밀번호 |
|---|---|---|
| `관리자` | `ADM001` | `admin1234!` |

주의: 이름 필드에 사번(`ADM001`)이 아니라 계정의 **이름(`관리자`)** 을 입력해야 합니다.

## 테스트

```bash
cd backend
../.venv/bin/python manage.py test          # 전체 179개 (단위 + API + 통합/보안)

cd frontend
npm run build                               # 프론트엔드 빌드 검증
```

## 주요 API

Base: `/api` (인증: Django Session, 변경 요청에는 `X-CSRFToken` 헤더 필요)

| 구분 | 엔드포인트 |
|---|---|
| 인증 | `POST /auth/login/` · `POST /auth/logout/` · `GET /auth/me/` |
| 직원 평가 | `GET /reviews/my/` · `GET /reviews/{id}/` · `PUT /reviews/{id}/answers/` · `POST /reviews/{id}/submit/` |
| 관리자 CRUD | `/admin/users/` · `/admin/departments/` · `/admin/review-periods/` · `/admin/questions/` · `/admin/reviews/` · `/admin/department-performances/` |
| 평가자/점수 | `POST /admin/reviews/{id}/evaluators/` · `POST /admin/reviews/{id}/calculate-score/` |
| 기간 상태 전환 | `POST /admin/review-periods/{id}/status/` |
| 모니터링/CSV | `GET /admin/monitoring/summary/` · `GET /admin/monitoring/export/` (UTF-8 BOM CSV) |

권한: 모든 Admin API는 `role=ADMIN`만 허용, 직원은 본인 Review만 접근 가능 (IDOR 방지).

## 점수 정책 (MVP 기본값)

```text
SCALE 1~5 → 0~100 정규화 ((score-1)/4×100, TEXT/선택형은 자동 채점 제외)
individual_score = Σ(정규화 점수 × 가중치) / Σ(가중치)     # 활성 문항 가중치 합 = 100
department_adjustment = (부서 성과 점수 - 70) × 0.20
final_score = clamp(individual_score + department_adjustment, 0, 100)
```

기준값 70/0.20은 예시 정책이며 `backend/scoring/services.py` 상수로 관리됩니다. 실제 운영 전 회사 평가 정책에 맞게 확정해야 합니다.

## 라이프사이클

```text
ReviewPeriod: DRAFT → OPEN → CLOSED   (OPEN 전환 시 활성 문항 가중치 합 100 강제)
Review:       NOT_STARTED → IN_PROGRESS → SUBMITTED   (제출 후 직원 수정/재제출 불가)
```
