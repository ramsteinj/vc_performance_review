import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Answer, Question, Review, ReviewPeriod
from .services import (
    AnswerValidationError,
    InvalidStatusTransition,
    QuestionLockedError,
    WeightTotalError,
    activate_question,
    add_choice,
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
