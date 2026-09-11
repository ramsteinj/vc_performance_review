import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import ReviewPeriod
from .services import InvalidStatusTransition, change_status, create_review_period


def period_data(**overrides):
    data = {
        "name": "2026 상반기 평가",
        "start_date": datetime.date(2026, 1, 1),
        "end_date": datetime.date(2026, 6, 30),
    }
    data.update(overrides)
    return data


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
        change_status(period, ReviewPeriod.Status.OPEN)
        change_status(period, ReviewPeriod.Status.CLOSED)
        for target in (ReviewPeriod.Status.DRAFT, ReviewPeriod.Status.OPEN):
            with self.assertRaises(InvalidStatusTransition):
                change_status(period, target)

    def test_same_status_is_noop(self):
        period = ReviewPeriod.objects.create(**period_data())
        returned = change_status(period, ReviewPeriod.Status.DRAFT)
        self.assertEqual(returned.status, ReviewPeriod.Status.DRAFT)
