from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Answer, Choice, Question, Review, ReviewPeriod


class InvalidStatusTransition(ValueError):
    pass


class QuestionLockedError(ValueError):
    pass


class WeightTotalError(ValueError):
    pass


class AnswerValidationError(ValueError):
    pass


class EvaluatorValidationError(ValueError):
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


def ensure_period_editable(review_period):
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
    ensure_period_editable(review_period)
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
    ensure_period_editable(question.review_period)
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
    ensure_period_editable(question.review_period)
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


def get_or_create_review(
    review_period,
    employee,
    *,
    primary_evaluator=None,
    secondary_evaluator=None,
):
    defaults = {}
    if primary_evaluator is not None:
        defaults["primary_evaluator"] = primary_evaluator
    if secondary_evaluator is not None:
        defaults["secondary_evaluator"] = secondary_evaluator
    return Review.objects.get_or_create(
        review_period=review_period,
        employee=employee,
        defaults=defaults,
    )


def _ensure_answerable(review, question):
    if review.status == Review.Status.SUBMITTED:
        raise AnswerValidationError("submitted review cannot be modified")
    if review.review_period.status != ReviewPeriod.Status.OPEN:
        raise AnswerValidationError("review period is not open")
    if question.review_period_id != review.review_period_id:
        raise AnswerValidationError(
            "question does not belong to this review period"
        )
    if not question.is_active:
        raise AnswerValidationError("question is not active")


def save_answer(review, question, *, answer_text="", score=None, choice_ids=None):
    _ensure_answerable(review, question)
    with transaction.atomic():
        answer, _ = Answer.objects.update_or_create(
            review=review,
            question=question,
            defaults={
                "answer_text": answer_text,
                "score": score,
            },
        )
        if choice_ids is not None:
            choices = list(question.choices.filter(id__in=set(choice_ids)))
            if len(choices) != len(set(choice_ids)):
                raise AnswerValidationError("choices must belong to the question")
            if (
                question.question_type == Question.QuestionType.SINGLE_CHOICE
                and len(choices) > 1
            ):
                raise AnswerValidationError(
                    "only one choice is allowed for SINGLE_CHOICE"
                )
            answer.selected_choices.set(choices)
        if review.status == Review.Status.NOT_STARTED:
            review.status = Review.Status.IN_PROGRESS
            review.save(update_fields=["status", "updated_at"])
    return answer


def get_progress(review):
    required_count = review.review_period.questions.filter(
        is_active=True, required=True
    ).count()
    if required_count == 0:
        return 100
    answered_count = review.answers.filter(
        question__is_active=True, question__required=True
    ).count()
    return int(answered_count * 100 / required_count)


@transaction.atomic
def submit_review(review):
    if review.status == Review.Status.SUBMITTED:
        raise AnswerValidationError("review is already submitted")
    if review.review_period.status != ReviewPeriod.Status.OPEN:
        raise AnswerValidationError("review period is not open")
    has_missing = (
        review.review_period.questions.filter(is_active=True, required=True)
        .exclude(id__in=review.answers.values_list("question_id", flat=True))
        .exists()
    )
    if has_missing:
        raise AnswerValidationError("all required questions must be answered")
    review.status = Review.Status.SUBMITTED
    review.submitted_at = timezone.now()
    review.save(update_fields=["status", "submitted_at", "updated_at"])
    return review


def _check_evaluator(employee, evaluator):
    if not evaluator.is_active:
        raise EvaluatorValidationError("evaluator must be an active user")
    if evaluator.id == employee.id:
        raise EvaluatorValidationError(
            "employee cannot be their own evaluator"
        )


def validate_evaluators(employee, primary_evaluator, secondary_evaluator=None):
    if primary_evaluator is None:
        raise EvaluatorValidationError("primary_evaluator is required")
    _check_evaluator(employee, primary_evaluator)
    if secondary_evaluator is not None:
        _check_evaluator(employee, secondary_evaluator)


def assign_evaluators(review, *, primary_evaluator, secondary_evaluator=None):
    if review.status == Review.Status.SUBMITTED:
        raise EvaluatorValidationError(
            "cannot change evaluators after submission"
        )
    validate_evaluators(review.employee, primary_evaluator, secondary_evaluator)
    review.primary_evaluator = primary_evaluator
    review.secondary_evaluator = secondary_evaluator
    review.save(
        update_fields=["primary_evaluator", "secondary_evaluator", "updated_at"]
    )
    return review
