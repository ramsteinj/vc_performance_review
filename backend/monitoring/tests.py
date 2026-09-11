import csv
import io

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from reviews.services import filter_reviews
from scoring.tests import make_review_set

from .services import get_response_summary

User = get_user_model()


class ReviewFilterServiceTests(TestCase):
    def setUp(self):
        self.review, _, self.department = make_review_set(
            employee_number="EMP001", submit=True
        )
        self.other, _, self.other_department = make_review_set(
            employee_number="EMP002",
            department_name="영업팀",
            submit=False,
            answer_scores=[None],
        )

    def test_filter_by_status(self):
        self.assertEqual(
            filter_reviews(status="SUBMITTED").count(), 1
        )
        self.assertEqual(filter_reviews(status="NOT_STARTED").count(), 1)

    def test_filter_by_employee(self):
        employee = User.objects.get(employee_number="EMP001")
        self.assertEqual(filter_reviews(employee_id=employee.id).count(), 1)

    def test_filter_by_department(self):
        self.assertEqual(
            filter_reviews(department_id=self.department.id).count(), 1
        )

    def test_filter_by_review_period(self):
        self.assertEqual(
            filter_reviews(review_period_id=self.review.review_period_id).count(), 1
        )

    def test_unfiltered_returns_all(self):
        self.assertEqual(filter_reviews().count(), 2)


class ResponseSummaryServiceTests(TestCase):
    def test_counts_and_rates(self):
        make_review_set(employee_number="EMP001", submit=True)
        make_review_set(
            employee_number="EMP002", submit=False, answer_scores=[4]
        )
        make_review_set(
            employee_number="EMP003", submit=False, answer_scores=[None]
        )
        summary = get_response_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["submitted"], 1)
        self.assertEqual(summary["in_progress"], 1)
        self.assertEqual(summary["not_started"], 1)
        self.assertEqual(summary["response_rate"], 33.3)

    def test_department_breakdown(self):
        review, _, department = make_review_set(
            employee_number="EMP001", submit=True
        )
        summary = get_response_summary()
        by_department = {
            item["department"]: item for item in summary["by_department"]
        }
        self.assertIn("개발팀-EMP001", by_department)
        entry = by_department["개발팀-EMP001"]
        self.assertEqual(entry["total"], 1)
        self.assertEqual(entry["submitted"], 1)
        self.assertEqual(entry["response_rate"], 100.0)

    def test_period_filter(self):
        make_review_set(employee_number="EMP001", submit=True)
        make_review_set(
            employee_number="EMP002", submit=False, answer_scores=[None]
        )
        from reviews.models import Review

        review = Review.objects.select_related("review_period").get(
            employee__employee_number="EMP001"
        )
        summary = get_response_summary(
            review_period_id=review.review_period_id
        )
        self.assertEqual(summary["total"], 1)


class MonitoringSummaryApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADM001",
            employee_number="ADM001",
            name="관리자",
            password="test-password-123!",
            role="ADMIN",
        )
        self.employee = User.objects.create_user(
            username="EMP009",
            employee_number="EMP009",
            name="홍길동",
            password="test-password-123!",
        )
        make_review_set(employee_number="EMP001", submit=True)
        make_review_set(
            employee_number="EMP002", submit=False, answer_scores=[None]
        )

    def test_employee_cannot_access(self):
        self.client.force_login(self.employee)
        response = self.client.get("/api/admin/monitoring/summary/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_get_summary(self):
        self.client.force_login(self.admin)
        response = self.client.get("/api/admin/monitoring/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(response.data["submitted"], 1)
        self.assertEqual(response.data["response_rate"], 50.0)

    def test_summary_with_department_filter(self):
        from reviews.models import Review

        review = Review.objects.select_related("employee__department").get(
            employee__employee_number="EMP001"
        )
        self.client.force_login(self.admin)
        response = self.client.get(
            "/api/admin/monitoring/summary/",
            {"department": review.employee.department_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 1)


class CsvExportApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADM001",
            employee_number="ADM001",
            name="관리자",
            password="test-password-123!",
            role="ADMIN",
        )
        self.employee = User.objects.create_user(
            username="EMP009",
            employee_number="EMP009",
            name="홍길동",
            password="test-password-123!",
        )
        self.review, _, _ = make_review_set(
            employee_number="EMP001",
            weights=(100,),
            score=3,
            performance_score=80,
            submit=True,
        )
        from scoring.services import calculate_and_store_final_score

        calculate_and_store_final_score(self.review)

    def get_csv_rows(self, query=""):
        self.client.force_login(self.admin)
        response = self.client.get(f"/api/admin/monitoring/export/{query}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        decoded = response.content.decode("utf-8-sig")
        return list(csv.reader(io.StringIO(decoded)))

    def test_employee_cannot_export(self):
        self.client.force_login(self.employee)
        response = self.client.get("/api/admin/monitoring/export/")
        self.assertEqual(response.status_code, 403)

    def test_content_type_is_csv(self):
        self.client.force_login(self.admin)
        response = self.client.get("/api/admin/monitoring/export/")
        self.assertIn("text/csv", response["Content-Type"])

    def test_headers(self):
        rows = self.get_csv_rows()
        header = rows[0]
        for expected in (
            "평가 기간",
            "부서",
            "사번",
            "이름",
            "상태",
            "1차 평가자",
            "2차 평가자",
            "개인 점수",
            "부서 점수",
            "부서 조정점수",
            "최종 점수",
            "제출일시",
        ):
            self.assertIn(expected, header)
        self.assertTrue(any(col.startswith("답변: ") for col in header))
        self.assertTrue(any(col.startswith("점수: ") for col in header))

    def test_data_row(self):
        rows = self.get_csv_rows()
        data = dict(zip(rows[0], rows[1]))
        self.assertEqual(data["사번"], "EMP001")
        self.assertEqual(data["이름"], "홍길동")
        self.assertEqual(data["상태"], "SUBMITTED")
        self.assertEqual(data["개인 점수"], "50.00")
        self.assertEqual(data["부서 점수"], "80.00")
        self.assertEqual(data["부서 조정점수"], "2.00")
        self.assertEqual(data["최종 점수"], "52.00")
        self.assertEqual(data["점수: [2026 상반기 평가] 문항 1"], "50.00")

    def test_status_filter_applies(self):
        rows = self.get_csv_rows("?status=NOT_STARTED")
        self.assertEqual(len(rows), 1)
