"""
spec 15 인수 기준 통합/보안 테스트 (Phase 9)

- 전체 평가 흐름 E2E (관리자 설정 → 직원 응답/제출 → 점수 계산 → 모니터링/CSV)
- Security: Admin API 보호, IDOR, client 변조 무시, submitted review 수정 차단
- Custom User / Data Integrity 제약 검증
"""
import csv
import datetime
import io

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from departments.models import Department
from reviews.models import Answer, Question, Review, ReviewPeriod
from reviews.services import get_or_create_review
from scoring.models import DepartmentPerformance, FinalScore

User = get_user_model()

PASSWORD = "test-password-123!"


def make_open_review_via_services(employee_number="EMP001"):
    period = ReviewPeriod.objects.create(
        name="2026 상반기 평가",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 6, 30),
    )
    Question.objects.create(
        review_period=period,
        text="직무 만족도",
        question_type=Question.QuestionType.SCALE,
        weight=100,
    )
    employee = User.objects.create_user(
        username=employee_number,
        employee_number=employee_number,
        name="홍길동",
        password=PASSWORD,
    )
    evaluator = User.objects.create_user(
        username=f"MGR-{employee_number}",
        employee_number=f"MGR-{employee_number}",
        name="평가자",
        password=PASSWORD,
    )
    review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
    return period, review


class Spec15FullFlowTests(APITestCase):
    """관리자 설정 → 직원 응답/제출 → 점수 계산 → 모니터링/CSV (E2E)"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADM001",
            employee_number="ADM001",
            name="관리자",
            password=PASSWORD,
            role="ADMIN",
        )
        self.employee = User.objects.create_user(
            username="EMP001",
            employee_number="EMP001",
            name="홍길동",
            password=PASSWORD,
        )
        self.evaluator = User.objects.create_user(
            username="MGR001",
            employee_number="MGR001",
            name="평가자",
            password=PASSWORD,
        )
        self.department = Department.objects.create(name="개발팀")
        self.employee.department = self.department
        self.employee.save()

    def test_full_evaluation_flow(self):
        # 1) 관리자: 평가 기간 생성
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/review-periods/",
            {
                "name": "2026 상반기",
                "start_date": "2026-01-01",
                "end_date": "2026-06-30",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "DRAFT")
        period_id = response.data["id"]

        # 2) 문항 2개 (가중치 60 + 40 = 100)
        for text, weight in (("직무 만족도", 60), ("성과 목표 달성도", 40)):
            response = self.client.post(
                "/api/admin/questions/",
                {
                    "review_period": period_id,
                    "text": text,
                    "question_type": "SCALE",
                    "weight": weight,
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201)

        # 3) OPEN 전환
        response = self.client.post(
            f"/api/admin/review-periods/{period_id}/status/",
            {"status": "OPEN"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "OPEN")

        # 4) 평가 대상자 생성 + 평가자 지정 (1차 필수, 2차 선택)
        response = self.client.post(
            "/api/admin/reviews/",
            {
                "review_period": period_id,
                "employee": self.employee.id,
                "primary_evaluator": self.evaluator.id,
                "secondary_evaluator": self.admin.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        review_id = response.data["id"]
        self.assertEqual(response.data["primary_evaluator"]["employee_number"], "MGR001")
        self.assertEqual(response.data["secondary_evaluator"]["employee_number"], "ADM001")

        # 5) 중복 Review 생성 차단
        response = self.client.post(
            "/api/admin/reviews/",
            {
                "review_period": period_id,
                "employee": self.employee.id,
                "primary_evaluator": self.evaluator.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 409)

        # 6) 부서 성과 점수 입력
        response = self.client.post(
            "/api/admin/department-performances/",
            {
                "review_period": period_id,
                "department": self.department.id,
                "performance_score": "80",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        # 7) 직원: Admin API 접근 차단
        self.client.force_login(self.employee)
        response = self.client.get("/api/admin/users/")
        self.assertEqual(response.status_code, 403)

        # 8) 직원: 내 평가 조회, 진행률 0
        response = self.client.get("/api/reviews/my/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["progress"], 0)

        # 9) IDOR: 타 직원 Review를 생성하고 직원 계정으로 접근 → 404
        other = User.objects.create_user(
            username="EMP002",
            employee_number="EMP002",
            name="다른 직원",
            password=PASSWORD,
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/reviews/",
            {
                "review_period": period_id,
                "employee": other.id,
                "primary_evaluator": self.evaluator.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        other_review_id = response.data["id"]

        self.client.force_login(self.employee)
        response = self.client.get(f"/api/reviews/{other_review_id}/")
        self.assertEqual(response.status_code, 404)

        # 10) 문항 응답 + 임시 저장 (client가 넣은 이상한 필드는 무시됨)
        response = self.client.get(f"/api/reviews/{review_id}/")
        self.assertEqual(response.status_code, 200)
        questions = response.data["questions"]
        self.assertEqual(len(questions), 2)

        response = self.client.put(
            f"/api/reviews/{review_id}/answers/",
            {
                "answers": [
                    {
                        "question": questions[0]["id"],
                        "score": 5,
                        "employee": other.id,
                        "role": "ADMIN",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["progress"], 50)
        self.assertEqual(response.data["status"], "IN_PROGRESS")
        other_review = Review.objects.get(id=other_review_id)
        self.assertEqual(other_review.answers.count(), 0)
        self.assertEqual(other_review.status, Review.Status.NOT_STARTED)

        # 11) 필수 문항 미응답 제출 차단
        response = self.client.post(f"/api/reviews/{review_id}/submit/")
        self.assertEqual(response.status_code, 400)

        # 12) 전체 응답 후 임시 저장 → 진행률 100
        response = self.client.put(
            f"/api/reviews/{review_id}/answers/",
            {
                "answers": [
                    {"question": questions[0]["id"], "score": 5},
                    {"question": questions[1]["id"], "score": 1},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["progress"], 100)

        # 13) 제출
        response = self.client.post(f"/api/reviews/{review_id}/submit/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "SUBMITTED")
        self.assertIsNotNone(response.data["submitted_at"])

        # 14) 제출 후 수정/재제출 차단
        response = self.client.put(
            f"/api/reviews/{review_id}/answers/",
            {"answers": [{"question": questions[0]["id"], "score": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(f"/api/reviews/{review_id}/submit/")
        self.assertEqual(response.status_code, 400)

        # 15) 관리자: 최종 점수 계산 (개인 60, 부서 80 → 조정 +2 → 62)
        self.client.force_login(self.admin)
        response = self.client.post(f"/api/admin/reviews/{review_id}/calculate-score/")
        self.assertEqual(response.status_code, 200)
        final_score = response.data["final_score"]
        self.assertEqual(final_score["individual_score"], "60.00")
        self.assertEqual(final_score["department_score"], "80.00")
        self.assertEqual(final_score["department_adjustment"], "2.00")
        self.assertEqual(final_score["final_score"], "62.00")

        # 16) 모니터링 현황
        response = self.client.get(
            "/api/admin/monitoring/summary/",
            {"review_period": period_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(response.data["submitted"], 1)
        self.assertEqual(response.data["not_started"], 1)

        # 17) 미응답자 조회
        response = self.client.get(
            "/api/admin/reviews/",
            {"review_period": period_id, "status": "NOT_STARTED"},
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["employee"]["employee_number"], "EMP002")

        # 18) CSV 다운로드 (UTF-8 BOM + 한글 헤더 + 점수)
        response = self.client.get(
            "/api/admin/monitoring/export/",
            {"review_period": period_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        decoded = response.content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(decoded)))
        data = dict(zip(rows[0], rows[1]))
        self.assertEqual(data["사번"], "EMP001")
        self.assertEqual(data["상태"], "SUBMITTED")
        self.assertEqual(data["개인 점수"], "60.00")
        self.assertEqual(data["최종 점수"], "62.00")


ADMIN_ENDPOINTS = [
    "/api/admin/users/",
    "/api/admin/departments/",
    "/api/admin/review-periods/",
    "/api/admin/questions/",
    "/api/admin/reviews/",
    "/api/admin/department-performances/",
    "/api/admin/monitoring/summary/",
    "/api/admin/monitoring/export/",
]


class AdminApiProtectionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADM001",
            employee_number="ADM001",
            name="관리자",
            password=PASSWORD,
            role="ADMIN",
        )
        self.employee = User.objects.create_user(
            username="EMP001",
            employee_number="EMP001",
            name="홍길동",
            password=PASSWORD,
        )

    def test_anonymous_blocked_on_all_admin_endpoints(self):
        for endpoint in ADMIN_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 403)

    def test_employee_blocked_on_all_admin_endpoints(self):
        self.client.force_login(self.employee)
        for endpoint in ADMIN_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 403)

    def test_admin_can_access_all_admin_endpoints(self):
        self.client.force_login(self.admin)
        for endpoint in ADMIN_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 200)


class ClientTrustTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADM001",
            employee_number="ADM001",
            name="관리자",
            password=PASSWORD,
            role="ADMIN",
        )
        self.employee = User.objects.create_user(
            username="EMP001",
            employee_number="EMP001",
            name="홍길동",
            password=PASSWORD,
        )

    def test_me_returns_request_user_not_client_user_id(self):
        self.client.force_login(self.employee)
        response = self.client.get("/api/auth/me/", {"user_id": self.admin.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["employee_number"], "EMP001")

    def test_client_role_field_does_not_escalate(self):
        self.client.force_login(self.employee)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.data["role"], "EMPLOYEE")

    def test_inactive_user_login_blocked(self):
        self.employee.is_active = False
        self.employee.save()
        response = self.client.post(
            "/api/auth/login/",
            {"name": "홍길동", "employee_number": "EMP001", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_login_response_excludes_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"name": "홍길동", "employee_number": "EMP001", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password", response.data)


class CustomUserIntegrityTests(TestCase):
    def test_user_inherits_abstractuser(self):
        self.assertTrue(issubclass(User, AbstractUser))

    def test_auth_user_model_setting(self):
        from django.conf import settings

        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_no_separate_employee_or_admin_tables(self):
        model_names = [
            model.__name__ for model in apps.get_app_config("accounts").get_models()
        ]
        self.assertEqual(model_names, ["User"])

    def test_review_references_auth_user_model(self):
        for field_name in ("employee", "primary_evaluator", "secondary_evaluator"):
            with self.subTest(field=field_name):
                field = Review._meta.get_field(field_name)
                self.assertIs(field.related_model, User)

    def test_employee_number_unique(self):
        User.objects.create_user(
            username="EMP001",
            employee_number="EMP001",
            name="홍길동",
            password=PASSWORD,
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create_user(
                    username="EMP001-dup",
                    employee_number="EMP001",
                    name="홍길순",
                    password=PASSWORD,
                )


class DataIntegrityTests(TestCase):
    def setUp(self):
        self.period, self.review = make_open_review_via_services()
        self.question = self.period.questions.first()

    def test_review_unique_per_period_and_employee(self):
        employee = User.objects.get(employee_number="EMP001")
        evaluator = User.objects.get(employee_number="MGR-EMP001")
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Review.objects.create(
                    review_period=self.period,
                    employee=employee,
                    primary_evaluator=evaluator,
                )

    def test_answer_unique_per_review_and_question(self):
        Answer.objects.create(review=self.review, question=self.question)
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Answer.objects.create(review=self.review, question=self.question)

    def test_department_performance_unique(self):
        department = Department.objects.create(name="개발팀")
        employee = User.objects.get(employee_number="EMP001")
        employee.department = department
        employee.save()
        DepartmentPerformance.objects.create(
            review_period=self.period,
            department=department,
            performance_score=80,
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                DepartmentPerformance.objects.create(
                    review_period=self.period,
                    department=department,
                    performance_score=70,
                )

    def test_final_score_is_one_to_one(self):
        FinalScore.objects.create(
            review=self.review,
            individual_score=50,
            department_score=70,
            department_adjustment=0,
            final_score=50,
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                FinalScore.objects.create(
                    review=self.review,
                    individual_score=60,
                    department_score=70,
                    department_adjustment=0,
                    final_score=60,
                )
