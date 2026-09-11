import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from departments.models import Department
from reviews.models import Question, ReviewPeriod
from reviews.services import (
    change_status,
    get_or_create_review,
    save_answer,
    submit_review,
)

from .models import DepartmentPerformance, FinalScore
from .services import (
    ScoringError,
    calculate_and_store_final_score,
    calculate_department_adjustment,
    calculate_final_score,
    calculate_individual_score,
    normalize_scale_score,
)

User = get_user_model()


def make_review_set(
    *,
    employee_number="EMP001",
    department_name="개발팀",
    weights=(100,),
    answer_scores=None,
    score=5,
    performance_score=None,
    submit=True,
):
    period = ReviewPeriod.objects.create(
        name="2026 상반기 평가",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 6, 30),
    )
    questions = []
    for index, weight in enumerate(weights):
        questions.append(
            Question.objects.create(
                review_period=period,
                text=f"문항 {index + 1}",
                question_type=Question.QuestionType.SCALE,
                weight=weight,
            )
        )
    department = Department.objects.create(name=f"{department_name}-{employee_number}")
    employee = User.objects.create_user(
        username=employee_number,
        employee_number=employee_number,
        name="홍길동",
        password="test-password-123!",
        department=department,
    )
    evaluator = User.objects.create_user(
        username=f"MGR-{employee_number}",
        employee_number=f"MGR-{employee_number}",
        name="평가자",
        password="test-password-123!",
    )
    change_status(period, ReviewPeriod.Status.OPEN)
    review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
    if answer_scores is None:
        answer_scores = [score] * len(questions)
    for question, answer_score in zip(questions, answer_scores):
        if answer_score is None:
            continue
        save_answer(review, question, score=answer_score)
    if submit:
        submit_review(review)
    if performance_score is not None:
        DepartmentPerformance.objects.create(
            review_period=period,
            department=department,
            performance_score=performance_score,
        )
    return review, questions, department


class ScaleNormalizationTests(TestCase):
    def test_scale_min_is_zero(self):
        self.assertEqual(normalize_scale_score(1), Decimal("0"))

    def test_scale_midpoint_is_fifty(self):
        self.assertEqual(normalize_scale_score(3), Decimal("50"))

    def test_scale_max_is_hundred(self):
        self.assertEqual(normalize_scale_score(5), Decimal("100"))

    def test_invalid_values_return_none(self):
        for invalid in (None, 0, 6, -1, "abc"):
            with self.subTest(value=invalid):
                self.assertIsNone(normalize_scale_score(invalid))


class IndividualScoreTests(TestCase):
    def test_weighted_average(self):
        review, questions, _ = make_review_set(
            weights=(60, 40), score=5, submit=False
        )
        save_answer(review, questions[1], score=1)
        result = calculate_individual_score(review)
        self.assertEqual(result, Decimal("60"))

    def test_text_question_excluded(self):
        review, _, _ = make_review_set(weights=(100,), score=5, submit=False)
        text_question = Question.objects.create(
            review_period=review.review_period,
            text="서술형 문항",
            question_type=Question.QuestionType.TEXT,
            weight=50,
        )
        save_answer(review, text_question, answer_text="의견")
        result = calculate_individual_score(review)
        self.assertEqual(result, Decimal("100"))

    def test_unanswered_question_excluded(self):
        review, _, _ = make_review_set(
            weights=(60, 40), answer_scores=[5, None], submit=False
        )
        result = calculate_individual_score(review)
        self.assertEqual(result, Decimal("100"))

    def test_invalid_score_excluded(self):
        review, questions, _ = make_review_set(
            weights=(60, 40), answer_scores=[4, None], submit=False
        )
        save_answer(review, questions[1], score=None, answer_text="메모")
        result = calculate_individual_score(review)
        self.assertEqual(result, Decimal("75"))

    def test_no_scorable_answers_returns_none(self):
        period = ReviewPeriod.objects.create(
            name="TEXT 전용 기간",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 6, 30),
        )
        text_question = Question.objects.create(
            review_period=period,
            text="서술형 문항",
            question_type=Question.QuestionType.TEXT,
            weight=100,
        )
        employee = User.objects.create_user(
            username="EMP010",
            employee_number="EMP010",
            name="직원",
            password="test-password-123!",
        )
        evaluator = User.objects.create_user(
            username="MGR010",
            employee_number="MGR010",
            name="평가자",
            password="test-password-123!",
        )
        change_status(period, ReviewPeriod.Status.OPEN)
        review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
        save_answer(review, text_question, answer_text="답변")
        self.assertIsNone(calculate_individual_score(review))


class DepartmentAdjustmentTests(TestCase):
    def test_baseline_score_means_zero(self):
        self.assertEqual(
            calculate_department_adjustment(Decimal("70")), Decimal("0")
        )

    def test_above_baseline_positive(self):
        self.assertEqual(
            calculate_department_adjustment(Decimal("80")), Decimal("2")
        )

    def test_below_baseline_negative(self):
        self.assertEqual(
            calculate_department_adjustment(Decimal("60")), Decimal("-2")
        )

    def test_none_returns_none(self):
        self.assertIsNone(calculate_department_adjustment(None))


class FinalScoreClampTests(TestCase):
    def test_clamped_to_hundred(self):
        self.assertEqual(
            calculate_final_score(Decimal("105"), Decimal("0")), Decimal("100")
        )

    def test_clamped_to_zero(self):
        self.assertEqual(
            calculate_final_score(Decimal("-5"), Decimal("0")), Decimal("0")
        )

    def test_normal_sum(self):
        self.assertEqual(
            calculate_final_score(Decimal("60"), Decimal("2")), Decimal("62")
        )

    def test_none_individual_returns_none(self):
        self.assertIsNone(calculate_final_score(None, Decimal("2")))

    def test_none_adjustment_treated_as_zero(self):
        self.assertEqual(
            calculate_final_score(Decimal("80"), None), Decimal("80")
        )


class FinalScoreCalculationTests(TestCase):
    def test_calculates_and_stores(self):
        review, _, _ = make_review_set(weights=(100,), score=3, performance_score=80)
        stored = calculate_and_store_final_score(review)
        self.assertEqual(stored.individual_score, Decimal("50.00"))
        self.assertEqual(stored.department_score, Decimal("80.00"))
        self.assertEqual(stored.department_adjustment, Decimal("2.00"))
        self.assertEqual(stored.final_score, Decimal("52.00"))

    def test_final_score_clamped_in_storage(self):
        review, _, _ = make_review_set(weights=(100,), score=5, performance_score=80)
        stored = calculate_and_store_final_score(review)
        self.assertEqual(stored.final_score, Decimal("100.00"))

    def test_missing_department_performance_raises(self):
        review, _, _ = make_review_set(weights=(100,), score=5, performance_score=None)
        with self.assertRaises(ScoringError):
            calculate_and_store_final_score(review)

    def test_recalculation_updates_existing(self):
        review, _, department = make_review_set(
            weights=(100,), score=3, performance_score=80
        )
        calculate_and_store_final_score(review)
        performance = DepartmentPerformance.objects.get(
            review_period=review.review_period, department=department
        )
        performance.performance_score = Decimal("60")
        performance.save()
        calculate_and_store_final_score(review)
        self.assertEqual(FinalScore.objects.filter(review=review).count(), 1)
        stored = FinalScore.objects.get(review=review)
        self.assertEqual(stored.final_score, Decimal("48.00"))


class DepartmentPerformanceModelTests(TestCase):
    def test_duplicate_period_and_department_rejected(self):
        review, _, department = make_review_set(performance_score=80)
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                DepartmentPerformance.objects.create(
                    review_period=review.review_period,
                    department=department,
                    performance_score=70,
                )

    def test_final_score_is_one_to_one(self):
        review, _, _ = make_review_set(performance_score=80)
        stored = calculate_and_store_final_score(review)
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                FinalScore.objects.create(review=review, **{
                    "individual_score": 1,
                    "department_score": 1,
                    "department_adjustment": 0,
                    "final_score": 1,
                })
        self.assertEqual(FinalScore.objects.filter(review=review).first(), stored)


class DepartmentPerformanceApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADM001",
            employee_number="ADM001",
            name="관리자",
            password="test-password-123!",
            role="ADMIN",
        )
        self.employee = User.objects.create_user(
            username="EMP001",
            employee_number="EMP001",
            name="홍길동",
            password="test-password-123!",
        )
        self.review, _, self.department = make_review_set(
            employee_number="EMP100", performance_score=None
        )

    def payload(self, **overrides):
        data = {
            "review_period": self.review.review_period.id,
            "department": self.department.id,
            "performance_score": "75",
        }
        data.update(overrides)
        return data

    def test_employee_cannot_access(self):
        self.client.force_login(self.employee)
        response = self.client.get("/api/admin/department-performances/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/department-performances/", self.payload(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["performance_score"], "75.00")

    def test_duplicate_rejected(self):
        DepartmentPerformance.objects.create(
            review_period=self.review.review_period,
            department=self.department,
            performance_score=80,
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/department-performances/", self.payload(), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_score_out_of_range_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/department-performances/",
            self.payload(performance_score="101"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_list(self):
        DepartmentPerformance.objects.create(
            review_period=self.review.review_period,
            department=self.department,
            performance_score=80,
        )
        self.client.force_login(self.admin)
        response = self.client.get("/api/admin/department-performances/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class CalculateScoreApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADM001",
            employee_number="ADM001",
            name="관리자",
            password="test-password-123!",
            role="ADMIN",
        )
        self.review, _, _ = make_review_set(
            weights=(100,), score=3, performance_score=80
        )
        self.review_without_department, _, _ = make_review_set(
            employee_number="EMP002",
            department_name="무소속",
            weights=(100,),
            score=3,
            performance_score=None,
        )

    def test_employee_cannot_calculate(self):
        employee = User.objects.get(employee_number="EMP001")
        self.client.force_login(employee)
        response = self.client.post(
            f"/api/admin/reviews/{self.review.id}/calculate-score/"
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_calculate(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/api/admin/reviews/{self.review.id}/calculate-score/"
        )
        self.assertEqual(response.status_code, 200)
        final_score = response.data["final_score"]
        self.assertEqual(final_score["individual_score"], "50.00")
        self.assertEqual(final_score["final_score"], "52.00")

    def test_missing_department_performance_returns_400(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/api/admin/reviews/{self.review_without_department.id}/calculate-score/"
        )
        self.assertEqual(response.status_code, 400)
