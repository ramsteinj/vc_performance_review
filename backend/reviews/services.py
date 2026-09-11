from django.db import transaction
from django.db.models import Sum

from .models import Choice, Question, ReviewPeriod


class InvalidStatusTransition(ValueError):
    pass


class QuestionLockedError(ValueError):
    pass


class WeightTotalError(ValueError):
    pass


ALLOWED_TRANSITIONS = {
    ReviewPeriod.Status.DRAFT: {ReviewPeriod.Status.OPEN},
    ReviewPeriod.Status.OPEN: {ReviewPeriod.Status.CLOSED},
    ReviewPeriod.Status.CLOSED: set(),
}

TARGET_WEIGHT_TOTAL = 100

CHOICE_TYPES = {
    Question.QuestionType.SINGLE_CHOICE,
    Question.QuestionType.MULTIPLE_CHOICE,
}

QUESTION_FIELDS = (
    "text",
    "description",
    "question_type",
    "weight",
    "display_order",
    "required",
    "is_active",
)


def create_review_period(*, name, start_date, end_date, description=""):
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    return ReviewPeriod.objects.create(
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date,
    )


@transaction.atomic
def change_status(review_period, new_status):
    current = review_period.status
    if new_status == current:
        return review_period
    if new_status not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransition(
            f"cannot change status from {current} to {new_status}"
        )
    if new_status == ReviewPeriod.Status.OPEN:
        validate_weight_total(review_period)
    review_period.status = new_status
    review_period.save(update_fields=["status", "updated_at"])
    return review_period


def _ensure_period_editable(review_period):
    if review_period.status != ReviewPeriod.Status.DRAFT:
        raise QuestionLockedError(
            "questions can only be modified while the period is DRAFT "
            f"(current status: {review_period.status})"
        )


def create_question(
    review_period,
    *,
    text,
    question_type,
    weight,
    description="",
    display_order=0,
    required=True,
):
    _ensure_period_editable(review_period)
    return Question.objects.create(
        review_period=review_period,
        text=text,
        description=description,
        question_type=question_type,
        weight=weight,
        display_order=display_order,
        required=required,
    )


def update_question(question, **fields):
    _ensure_period_editable(question.review_period)
    unknown = set(fields) - set(QUESTION_FIELDS)
    if unknown:
        raise ValueError(f"unknown question fields: {sorted(unknown)}")
    for field, value in fields.items():
        setattr(question, field, value)
    question.save()
    return question


def deactivate_question(question):
    return update_question(question, is_active=False)


def activate_question(question):
    return update_question(question, is_active=True)


def add_choice(question, *, text, display_order=0, score=None):
    _ensure_period_editable(question.review_period)
    if question.question_type not in CHOICE_TYPES:
        raise ValueError("choices are only allowed for choice-type questions")
    return Choice.objects.create(
        question=question,
        text=text,
        display_order=display_order,
        score=score,
    )


def get_weight_total(review_period):
    return (
        review_period.questions.filter(is_active=True)
        .aggregate(total=Sum("weight"))["total"]
        or 0
    )


def validate_weight_total(review_period):
    total = get_weight_total(review_period)
    if total != TARGET_WEIGHT_TOTAL:
        raise WeightTotalError(
            f"active question weight total must be {TARGET_WEIGHT_TOTAL}, got {total}"
        )
    return total
