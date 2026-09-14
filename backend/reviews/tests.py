import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from .models import Answer, Question, Review, ReviewPeriod
from .services import (
    AnswerValidationError,
    EvaluatorValidationError,
    InvalidStatusTransition,
    QuestionLockedError,
    WeightTotalError,
    activate_question,
    add_choice,
    assign_evaluators,
    change_status,
    create_question,
    create_review_period,
    deactivate_question,
    get_or_create_review,
    get_progress,
    get_weight_total,
    save_answer,
    submit_review,
    update_question,
    validate_evaluators,
    validate_weight_total,
)

User = get_user_model()


def period_data(**overrides):
    data = {
        "name": "2026 상반기 평가",
        "start_date": datetime.date(2026, 1, 1),
        "end_date": datetime.date(2026, 6, 30),
    }
    data.update(overrides)
    return data


def make_question(period, **overrides):
    data = {
        "text": "직무 만족도를 평가하세요.",
        "question_type": Question.QuestionType.SCALE,
        "weight": 100,
    }
    data.update(overrides)
    return Question.objects.create(review_period=period, **data)


class ReviewPeriodModelTests(TestCase):
    def test_default_status_is_draft(self):
        period = ReviewPeriod.objects.create(**period_data())
        self.assertEqual(period.status, ReviewPeriod.Status.DRAFT)

    def test_start_date_must_not_be_after_end_date(self):
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                ReviewPeriod.objects.create(
                    **period_data(end_date=datetime.date(2025, 12, 31))
                )


class ReviewPeriodServiceTests(TestCase):
    def test_create_review_period(self):
        period = create_review_period(**period_data(description="설명"))
        self.assertEqual(period.status, ReviewPeriod.Status.DRAFT)
        self.assertEqual(period.name, "2026 상반기 평가")

    def test_create_rejects_reversed_dates(self):
        with self.assertRaises(ValueError):
            create_review_period(
                name="잘못된 기간",
                start_date=datetime.date(2026, 6, 30),
                end_date=datetime.date(2026, 1, 1),
            )

    def test_draft_to_open_to_closed(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period)
        change_status(period, ReviewPeriod.Status.OPEN)
        self.assertEqual(period.status, ReviewPeriod.Status.OPEN)
        change_status(period, ReviewPeriod.Status.CLOSED)
        period.refresh_from_db()
        self.assertEqual(period.status, ReviewPeriod.Status.CLOSED)

    def test_draft_to_closed_rejected(self):
        period = ReviewPeriod.objects.create(**period_data())
        with self.assertRaises(InvalidStatusTransition):
            change_status(period, ReviewPeriod.Status.CLOSED)

    def test_closed_is_terminal(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period)
        change_status(period, ReviewPeriod.Status.OPEN)
        change_status(period, ReviewPeriod.Status.CLOSED)
        for target in (ReviewPeriod.Status.DRAFT, ReviewPeriod.Status.OPEN):
            with self.assertRaises(InvalidStatusTransition):
                change_status(period, target)

    def test_same_status_is_noop(self):
        period = ReviewPeriod.objects.create(**period_data())
        returned = change_status(period, ReviewPeriod.Status.DRAFT)
        self.assertEqual(returned.status, ReviewPeriod.Status.DRAFT)


class QuestionModelTests(TestCase):
    def test_question_belongs_to_period(self):
        period = ReviewPeriod.objects.create(**period_data())
        question = make_question(period)
        self.assertEqual(period.questions.count(), 1)
        self.assertEqual(question.review_period, period)

    def test_all_question_types_allowed(self):
        period = ReviewPeriod.objects.create(**period_data())
        for index, qtype in enumerate(Question.QuestionType.values):
            question = make_question(
                period,
                text=f"문항 {qtype}",
                question_type=qtype,
                weight=1,
            )
            self.assertEqual(question.question_type, qtype)
            self.assertEqual(index + 1, period.questions.count())


class ChoiceTests(TestCase):
    def make_single_choice_question(self):
        period = ReviewPeriod.objects.create(**period_data())
        return make_question(
            period,
            text="근속 연수를 선택하세요.",
            question_type=Question.QuestionType.SINGLE_CHOICE,
        )

    def test_add_choice(self):
        question = self.make_single_choice_question()
        choice = add_choice(question, text="3년", display_order=1, score=80)
        self.assertEqual(question.choices.count(), 1)
        self.assertEqual(choice.score, 80)

    def test_choice_score_defaults_to_none(self):
        question = self.make_single_choice_question()
        choice = add_choice(question, text="1년 미만")
        self.assertIsNone(choice.score)

    def test_add_choice_rejected_on_text_question(self):
        period = ReviewPeriod.objects.create(**period_data())
        question = make_question(
            period, question_type=Question.QuestionType.TEXT
        )
        with self.assertRaises(ValueError):
            add_choice(question, text="해당 없음")


class WeightTotalTests(TestCase):
    def test_get_weight_total_counts_only_active(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period, text="활성 1", weight=60)
        make_question(period, text="활성 2", weight=40)
        inactive = make_question(period, text="비활성", weight=50)
        deactivate_question(inactive)
        self.assertEqual(get_weight_total(period), 100)

    def test_validate_weight_total_raises_when_not_100(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period, weight=50)
        with self.assertRaises(WeightTotalError):
            validate_weight_total(period)

    def test_open_requires_weight_total_of_100(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period, weight=50)
        with self.assertRaises(WeightTotalError):
            change_status(period, ReviewPeriod.Status.OPEN)

    def test_open_succeeds_when_weight_total_is_100(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period, weight=100)
        change_status(period, ReviewPeriod.Status.OPEN)
        self.assertEqual(period.status, ReviewPeriod.Status.OPEN)


class QuestionLockTests(TestCase):
    def make_open_period(self):
        period = ReviewPeriod.objects.create(**period_data())
        question = make_question(period, weight=100)
        change_status(period, ReviewPeriod.Status.OPEN)
        return period, question

    def test_open_period_blocks_question_changes(self):
        period, question = self.make_open_period()
        with self.assertRaises(QuestionLockedError):
            create_question(
                period,
                text="새 문항",
                question_type=Question.QuestionType.TEXT,
                weight=10,
            )
        with self.assertRaises(QuestionLockedError):
            update_question(question, weight=50)
        with self.assertRaises(QuestionLockedError):
            deactivate_question(question)
        with self.assertRaises(QuestionLockedError):
            add_choice(question, text="선택지")

    def test_closed_period_blocks_question_changes(self):
        period, question = self.make_open_period()
        change_status(period, ReviewPeriod.Status.CLOSED)
        with self.assertRaises(QuestionLockedError):
            update_question(question, text="수정 시도")

    def test_draft_allows_question_changes(self):
        period = ReviewPeriod.objects.create(**period_data())
        question = create_question(
            period,
            text="업무 난이도",
            question_type=Question.QuestionType.SCALE,
            weight=50,
        )
        update_question(question, weight=60, display_order=2)
        self.assertEqual(question.weight, 60)
        deactivate_question(question)
        self.assertFalse(question.is_active)
        activate_question(question)
        self.assertTrue(question.is_active)

    def test_update_question_rejects_unknown_fields(self):
        period = ReviewPeriod.objects.create(**period_data())
        question = make_question(period)
        with self.assertRaises(ValueError):
            update_question(question, bogus_field=1)


def make_user(employee_number="EMP001", **overrides):
    data = {
        "username": employee_number,
        "employee_number": employee_number,
        "name": "홍길동",
        "password": "test-password-123!",
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_open_review(
    *, employee_number="EMP001", evaluator_number="MGR001", question_weights=(100,)
):
    period = ReviewPeriod.objects.create(**period_data())
    for index, weight in enumerate(question_weights):
        make_question(period, text=f"문항 {index + 1}", weight=weight)
    employee = make_user(employee_number)
    evaluator = make_user(evaluator_number, name="평가자")
    change_status(period, ReviewPeriod.Status.OPEN)
    review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
    return period, review


def answer_all_required(review, **kwargs):
    for question in review.review_period.questions.filter(
        is_active=True, required=True
    ):
        save_answer(review, question, **kwargs)


class ReviewModelTests(TestCase):
    def test_default_status_is_not_started(self):
        _, review = make_open_review()
        self.assertEqual(review.status, Review.Status.NOT_STARTED)
        self.assertIsNone(review.submitted_at)

    def test_secondary_evaluator_optional(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period)
        employee = make_user("EMP001")
        evaluator = make_user("MGR001", name="평가자")
        change_status(period, ReviewPeriod.Status.OPEN)
        review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
        self.assertIsNone(review.secondary_evaluator)

    def test_duplicate_review_for_same_period_and_employee(self):
        period, _ = make_open_review()
        employee = User.objects.get(employee_number="EMP001")
        evaluator = User.objects.get(employee_number="MGR001")
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Review.objects.create(
                    review_period=period,
                    employee=employee,
                    primary_evaluator=evaluator,
                )

    def test_same_employee_can_have_reviews_in_different_periods(self):
        _, first = make_open_review()
        second_period = ReviewPeriod.objects.create(
            name="2026 하반기 평가",
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 12, 31),
        )
        make_question(second_period)
        employee = User.objects.get(employee_number="EMP001")
        evaluator = User.objects.get(employee_number="MGR001")
        change_status(second_period, ReviewPeriod.Status.OPEN)
        second, created = get_or_create_review(
            second_period, employee, primary_evaluator=evaluator
        )
        self.assertTrue(created)
        self.assertNotEqual(first.id, second.id)


class AnswerModelTests(TestCase):
    def test_duplicate_answer_for_same_review_and_question(self):
        _, review = make_open_review()
        question = review.review_period.questions.first()
        save_answer(review, question)
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Answer.objects.create(review=review, question=question)


class ReviewServiceTests(TestCase):
    def test_get_or_create_review_is_idempotent(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period)
        employee = make_user("EMP001")
        evaluator = make_user("MGR001", name="평가자")
        first, created_first = get_or_create_review(
            period, employee, primary_evaluator=evaluator
        )
        second, created_second = get_or_create_review(
            period, employee, primary_evaluator=evaluator
        )
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.id, second.id)

    def test_create_requires_primary_evaluator(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period)
        employee = make_user("EMP001")
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                get_or_create_review(period, employee)


class AnswerServiceTests(TestCase):
    def test_save_answer_upserts(self):
        _, review = make_open_review()
        question = review.review_period.questions.first()
        save_answer(review, question, answer_text="초안")
        save_answer(review, question, answer_text="수정본")
        self.assertEqual(review.answers.count(), 1)
        self.assertEqual(review.answers.first().answer_text, "수정본")

    def test_save_answer_moves_status_to_in_progress(self):
        _, review = make_open_review()
        question = review.review_period.questions.first()
        save_answer(review, question)
        review.refresh_from_db()
        self.assertEqual(review.status, Review.Status.IN_PROGRESS)

    def test_save_answer_rejected_when_period_not_open(self):
        period = ReviewPeriod.objects.create(**period_data())
        question = make_question(period)
        employee = make_user("EMP001")
        evaluator = make_user("MGR001", name="평가자")
        review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
        with self.assertRaises(AnswerValidationError):
            save_answer(review, question)

    def test_save_answer_rejected_after_submit(self):
        _, review = make_open_review()
        question = review.review_period.questions.first()
        save_answer(review, question)
        submit_review(review)
        with self.assertRaises(AnswerValidationError):
            save_answer(review, question, answer_text="제출 후 수정")

    def test_save_answer_rejected_for_question_of_other_period(self):
        _, review = make_open_review()
        other_period = ReviewPeriod.objects.create(
            name="다른 기간",
            start_date=datetime.date(2027, 1, 1),
            end_date=datetime.date(2027, 6, 30),
        )
        other_question = make_question(other_period, text="다른 기간 문항")
        with self.assertRaises(AnswerValidationError):
            save_answer(review, other_question)

    def test_save_answer_rejected_for_inactive_question(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period, text="활성", weight=100)
        inactive_question = make_question(period, text="비활성", weight=50)
        deactivate_question(inactive_question)
        employee = make_user("EMP001")
        evaluator = make_user("MGR001", name="평가자")
        change_status(period, ReviewPeriod.Status.OPEN)
        review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
        with self.assertRaises(AnswerValidationError):
            save_answer(review, inactive_question)

    def test_single_choice_accepts_only_one_choice(self):
        period = ReviewPeriod.objects.create(**period_data())
        question = make_question(
            period,
            text="근속 연수",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            weight=100,
        )
        first = add_choice(question, text="1년")
        second = add_choice(question, text="3년")
        employee = make_user("EMP001")
        evaluator = make_user("MGR001", name="평가자")
        change_status(period, ReviewPeriod.Status.OPEN)
        review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)

        save_answer(review, question, choice_ids=[first.id])
        saved_ids = list(
            review.answers.first().selected_choices.values_list("id", flat=True)
        )
        self.assertEqual(saved_ids, [first.id])
        with self.assertRaises(AnswerValidationError):
            save_answer(review, question, choice_ids=[first.id, second.id])

    def test_choices_must_belong_to_question(self):
        period = ReviewPeriod.objects.create(**period_data())
        question = make_question(
            period,
            text="근속 연수",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            weight=50,
        )
        other_question = make_question(
            period,
            text="다른 문항",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            weight=50,
        )
        stranger = add_choice(other_question, text="위 선택지")
        employee = make_user("EMP001")
        evaluator = make_user("MGR001", name="평가자")
        change_status(period, ReviewPeriod.Status.OPEN)
        review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
        with self.assertRaises(AnswerValidationError):
            save_answer(review, question, choice_ids=[stranger.id])


class ProgressTests(TestCase):
    def test_progress_is_zero_before_answering(self):
        _, review = make_open_review(question_weights=(50, 50))
        self.assertEqual(get_progress(review), 0)

    def test_progress_is_partial(self):
        _, review = make_open_review(question_weights=(50, 50))
        save_answer(review, review.review_period.questions.first())
        self.assertEqual(get_progress(review), 50)

    def test_progress_is_complete(self):
        _, review = make_open_review(question_weights=(50, 50))
        answer_all_required(review)
        self.assertEqual(get_progress(review), 100)

    def test_progress_ignores_inactive_required_questions(self):
        period = ReviewPeriod.objects.create(**period_data())
        active_question = make_question(period, text="활성", weight=100)
        inactive_question = make_question(period, text="비활성", weight=50)
        deactivate_question(inactive_question)
        employee = make_user("EMP001")
        evaluator = make_user("MGR001", name="평가자")
        change_status(period, ReviewPeriod.Status.OPEN)
        review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
        save_answer(review, active_question)
        self.assertEqual(get_progress(review), 100)


class SubmitReviewTests(TestCase):
    def test_submit_requires_all_required_answers(self):
        _, review = make_open_review(question_weights=(50, 50))
        save_answer(review, review.review_period.questions.first())
        with self.assertRaises(AnswerValidationError):
            submit_review(review)

    def test_submit_success(self):
        _, review = make_open_review(question_weights=(50, 50))
        answer_all_required(review)
        submitted = submit_review(review)
        self.assertEqual(submitted.status, Review.Status.SUBMITTED)
        self.assertIsNotNone(submitted.submitted_at)
        review.refresh_from_db()
        self.assertEqual(review.status, Review.Status.SUBMITTED)

    def test_resubmit_forbidden(self):
        _, review = make_open_review()
        answer_all_required(review)
        submit_review(review)
        with self.assertRaises(AnswerValidationError):
            submit_review(review)

    def test_submit_rejected_when_period_not_open(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period)
        employee = make_user("EMP001")
        evaluator = make_user("MGR001", name="평가자")
        review, _ = get_or_create_review(period, employee, primary_evaluator=evaluator)
        with self.assertRaises(AnswerValidationError):
            submit_review(review)


class ReviewPeriodAdminApiTests(APITestCase):
    def setUp(self):
        self.admin = make_user("ADM001", name="관리자", role="ADMIN")
        self.employee = make_user("EMP001", name="홍길동")

    def test_employee_cannot_access_admin_api(self):
        self.client.force_login(self.employee)
        response = self.client.get("/api/admin/review-periods/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_review_period(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/review-periods/",
            period_data(description="API 생성"),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "DRAFT")

    def test_admin_cannot_create_reversed_dates(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/review-periods/",
            period_data(end_date=datetime.date(2025, 12, 31)),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_status_change_to_open_requires_weight_total(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period, weight=50)
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/api/admin/review-periods/{period.id}/status/",
            {"status": "OPEN"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_status_change_to_open(self):
        period = ReviewPeriod.objects.create(**period_data())
        make_question(period, weight=100)
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/api/admin/review-periods/{period.id}/status/",
            {"status": "OPEN"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "OPEN")

    def test_status_change_rejects_invalid_value(self):
        period = ReviewPeriod.objects.create(**period_data())
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/api/admin/review-periods/{period.id}/status/",
            {"status": "PAUSED"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class QuestionAdminApiTests(APITestCase):
    def setUp(self):
        self.admin = make_user("ADM001", name="관리자", role="ADMIN")
        self.employee = make_user("EMP001", name="홍길동")
        self.period = ReviewPeriod.objects.create(**period_data())

    def question_payload(self, **overrides):
        data = {
            "review_period": self.period.id,
            "text": "직무 만족도를 평가하세요.",
            "question_type": "SCALE",
            "weight": 100,
        }
        data.update(overrides)
        return data

    def test_employee_cannot_create_question(self):
        self.client.force_login(self.employee)
        response = self.client.post(
            "/api/admin/questions/", self.question_payload(), format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_question(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/questions/", self.question_payload(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.period.questions.count(), 1)

    def test_create_on_open_period_rejected(self):
        make_question(self.period, weight=100)
        change_status(self.period, ReviewPeriod.Status.OPEN)
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/questions/",
            self.question_payload(text="새 문항"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_update_question_in_draft(self):
        question = make_question(self.period, weight=50)
        self.client.force_login(self.admin)
        response = self.client.patch(
            f"/api/admin/questions/{question.id}/",
            {"weight": 60},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        question.refresh_from_db()
        self.assertEqual(question.weight, 60)

    def test_admin_can_put_question_with_unchanged_review_period(self):
        question = make_question(self.period, weight=50)
        self.client.force_login(self.admin)
        response = self.client.put(
            f"/api/admin/questions/{question.id}/",
            self.question_payload(weight=60, description="수정"),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        question.refresh_from_db()
        self.assertEqual(question.weight, 60)
        self.assertEqual(question.review_period_id, self.period.id)

    def test_update_rejects_changed_review_period(self):
        question = make_question(self.period, weight=50)
        other_period = ReviewPeriod.objects.create(**period_data())
        self.client.force_login(self.admin)
        response = self.client.patch(
            f"/api/admin/questions/{question.id}/",
            {"review_period": other_period.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        question.refresh_from_db()
        self.assertEqual(question.review_period_id, self.period.id)

    def test_update_on_open_period_rejected(self):
        question = make_question(self.period, weight=100)
        change_status(self.period, ReviewPeriod.Status.OPEN)
        self.client.force_login(self.admin)
        response = self.client.patch(
            f"/api/admin/questions/{question.id}/",
            {"weight": 50},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_destroy_deletes_question(self):
        question = make_question(self.period, weight=100)
        self.client.force_login(self.admin)
        response = self.client.delete(f"/api/admin/questions/{question.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Question.objects.filter(id=question.id).exists())

    def test_destroy_on_open_period_rejected(self):
        question = make_question(self.period, weight=100)
        change_status(self.period, ReviewPeriod.Status.OPEN)
        self.client.force_login(self.admin)
        response = self.client.delete(f"/api/admin/questions/{question.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Question.objects.filter(id=question.id).exists())

    def test_choices_create_and_list(self):
        question = make_question(
            self.period,
            text="근속 연수",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            weight=100,
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/api/admin/questions/{question.id}/choices/",
            {"text": "1년", "score": 20},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        listing = self.client.get(f"/api/admin/questions/{question.id}/choices/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)

    def test_choice_on_text_question_rejected(self):
        question = make_question(
            self.period,
            question_type=Question.QuestionType.TEXT,
            weight=100,
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/api/admin/questions/{question.id}/choices/",
            {"text": "해당 없음"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_choice(self):
        question = make_question(
            self.period,
            text="근속 연수",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            weight=100,
        )
        choice = add_choice(question, text="1년")
        self.client.force_login(self.admin)
        response = self.client.delete(
            f"/api/admin/questions/{question.id}/choices/{choice.id}/"
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(question.choices.count(), 0)


class EvaluatorServiceTests(TestCase):
    def make_submitted_review(self):
        _, review = make_open_review()
        answer_all_required(review)
        submit_review(review)
        return review

    def test_assign_evaluators(self):
        _, review = make_open_review()
        primary = make_user("MGR011", name="1차 평가자")
        secondary = make_user("MGR012", name="2차 평가자")
        assign_evaluators(
            review,
            primary_evaluator=primary,
            secondary_evaluator=secondary,
        )
        review.refresh_from_db()
        self.assertEqual(review.primary_evaluator, primary)
        self.assertEqual(review.secondary_evaluator, secondary)

    def test_secondary_evaluator_optional(self):
        _, review = make_open_review()
        primary = make_user("MGR011", name="1차 평가자")
        returned = assign_evaluators(review, primary_evaluator=primary)
        self.assertIsNone(returned.secondary_evaluator)

    def test_inactive_evaluator_rejected(self):
        _, review = make_open_review()
        inactive = make_user("MGR011", name="비활성 평가자")
        User.objects.filter(employee_number="MGR011").update(is_active=False)
        inactive.refresh_from_db()
        with self.assertRaises(EvaluatorValidationError):
            assign_evaluators(review, primary_evaluator=inactive)

    def test_self_evaluator_rejected(self):
        _, review = make_open_review()
        employee = User.objects.get(employee_number="EMP001")
        manager = make_user("MGR011", name="평가자")
        with self.assertRaises(EvaluatorValidationError):
            assign_evaluators(review, primary_evaluator=employee)
        with self.assertRaises(EvaluatorValidationError):
            assign_evaluators(
                review,
                primary_evaluator=manager,
                secondary_evaluator=employee,
            )

    def test_change_after_submission_rejected(self):
        review = self.make_submitted_review()
        manager = make_user("MGR011", name="새 평가자")
        with self.assertRaises(EvaluatorValidationError):
            assign_evaluators(review, primary_evaluator=manager)

    def test_validate_evaluators_requires_primary(self):
        employee = make_user("EMP001")
        with self.assertRaises(EvaluatorValidationError):
            validate_evaluators(employee, None)


class EvaluatorApiTests(APITestCase):
    def setUp(self):
        self.admin = make_user("ADM001", name="관리자", role="ADMIN")
        self.employee = make_user("EMP001", name="홍길동")
        self.manager = make_user("MGR001", name="평가자")
        self.period = ReviewPeriod.objects.create(**period_data())
        make_question(self.period, weight=100)

    def create_review_payload(self, **overrides):
        data = {
            "review_period": self.period.id,
            "employee": self.employee.id,
            "primary_evaluator": self.manager.id,
        }
        data.update(overrides)
        return data

    def test_employee_cannot_create_review(self):
        self.client.force_login(self.employee)
        response = self.client.post(
            "/api/admin/reviews/", self.create_review_payload(), format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_review_with_evaluators(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/reviews/", self.create_review_payload(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["employee"]["employee_number"], "EMP001")
        self.assertEqual(response.data["primary_evaluator"]["employee_number"], "MGR001")

    def test_duplicate_review_returns_409(self):
        get_or_create_review(self.period, self.employee, primary_evaluator=self.manager)
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/reviews/", self.create_review_payload(), format="json"
        )
        self.assertEqual(response.status_code, 409)

    def test_self_evaluator_rejected(self):
        self.client.force_login(self.admin)
        payload = self.create_review_payload(primary_evaluator=self.employee.id)
        response = self.client.post("/api/admin/reviews/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_inactive_evaluator_rejected(self):
        inactive = make_user("MGR009", name="비활성")
        User.objects.filter(employee_number="MGR009").update(is_active=False)
        self.client.force_login(self.admin)
        payload = self.create_review_payload(primary_evaluator=inactive.id)
        response = self.client.post("/api/admin/reviews/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_assign_evaluators_endpoint(self):
        review, _ = get_or_create_review(
            self.period, self.employee, primary_evaluator=self.manager
        )
        secondary = make_user("MGR002", name="2차 평가자")
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/api/admin/reviews/{review.id}/evaluators/",
            {"primary_evaluator": self.manager.id, "secondary_evaluator": secondary.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.secondary_evaluator, secondary)

    def test_employee_cannot_assign_evaluators(self):
        review, _ = get_or_create_review(
            self.period, self.employee, primary_evaluator=self.manager
        )
        self.client.force_login(self.employee)
        response = self.client.post(
            f"/api/admin/reviews/{review.id}/evaluators/",
            {"primary_evaluator": self.manager.id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class EmployeeReviewApiTests(APITestCase):
    def setUp(self):
        self.period, self.review = make_open_review()
        self.question = self.review.review_period.questions.first()
        self.other_period, self.other_review = make_open_review(
            employee_number="EMP002", evaluator_number="MGR002"
        )

    def login_employee(self, number="EMP001"):
        self.client.force_login(User.objects.get(employee_number=number))

    def test_my_requires_authentication(self):
        response = self.client.get("/api/reviews/my/")
        self.assertEqual(response.status_code, 403)

    def test_my_reviews_returns_only_own(self):
        self.login_employee()
        response = self.client.get("/api/reviews/my/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.review.id)
        self.assertIn("progress", response.data[0])

    def test_retrieve_own_review_includes_questions_and_progress(self):
        self.login_employee()
        response = self.client.get(f"/api/reviews/{self.review.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["progress"], 0)
        self.assertEqual(len(response.data["questions"]), 1)

    def test_retrieve_other_employee_review_forbidden(self):
        self.login_employee()
        response = self.client.get(f"/api/reviews/{self.other_review.id}/")
        self.assertEqual(response.status_code, 404)

    def test_put_answers_saves_and_updates_progress(self):
        self.login_employee()
        response = self.client.put(
            f"/api/reviews/{self.review.id}/answers/",
            {
                "answers": [
                    {"question": self.question.id, "answer_text": "좋음", "score": 4}
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "IN_PROGRESS")
        self.assertEqual(response.data["progress"], 100)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, Review.Status.IN_PROGRESS)

    def test_answers_rejected_when_period_not_open(self):
        draft_period = ReviewPeriod.objects.create(
            name="DRAFT 기간",
            start_date=datetime.date(2027, 1, 1),
            end_date=datetime.date(2027, 6, 30),
        )
        make_question(draft_period, weight=100)
        employee = User.objects.get(employee_number="EMP001")
        manager = User.objects.get(employee_number="MGR001")
        review, _ = get_or_create_review(
            draft_period, employee, primary_evaluator=manager
        )
        self.login_employee()
        response = self.client.put(
            f"/api/reviews/{review.id}/answers/",
            {"answers": [{"question": draft_period.questions.first().id}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_answers_rejected(self):
        self.login_employee()
        response = self.client.put(
            f"/api/reviews/{self.review.id}/answers/",
            {"answers": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_submit_flow(self):
        self.login_employee()
        self.client.put(
            f"/api/reviews/{self.review.id}/answers/",
            {"answers": [{"question": self.question.id, "score": 4}]},
            format="json",
        )
        response = self.client.post(f"/api/reviews/{self.review.id}/submit/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "SUBMITTED")
        self.assertIsNotNone(response.data["submitted_at"])

    def test_submit_blocked_until_required_answered(self):
        self.login_employee()
        response = self.client.post(f"/api/reviews/{self.review.id}/submit/")
        self.assertEqual(response.status_code, 400)

    def test_resubmit_rejected(self):
        self.login_employee()
        answer_all_required(self.review)
        submit_review(self.review)
        response = self.client.post(f"/api/reviews/{self.review.id}/submit/")
        self.assertEqual(response.status_code, 400)

    def test_modify_after_submit_rejected(self):
        self.login_employee()
        answer_all_required(self.review)
        submit_review(self.review)
        response = self.client.put(
            f"/api/reviews/{self.review.id}/answers/",
            {"answers": [{"question": self.question.id, "answer_text": "수정"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_submit_other_employee_review(self):
        self.login_employee()
        response = self.client.post(f"/api/reviews/{self.other_review.id}/submit/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_answer_other_employee_review(self):
        self.login_employee()
        other_question = self.other_review.review_period.questions.first()
        response = self.client.put(
            f"/api/reviews/{self.other_review.id}/answers/",
            {"answers": [{"question": other_question.id}]},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
