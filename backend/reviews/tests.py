import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Question, ReviewPeriod
from .services import (
    InvalidStatusTransition,
    QuestionLockedError,
    WeightTotalError,
    activate_question,
    add_choice,
    change_status,
    create_question,
    create_review_period,
    deactivate_question,
    get_weight_total,
    update_question,
    validate_weight_total,
)


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
