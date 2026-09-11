from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.utils import timezone

from reviews.models import Question

from .models import DepartmentPerformance, FinalScore

SCALE_MIN = Decimal("1")
SCALE_MAX = Decimal("5")
DEPARTMENT_BASELINE = Decimal("70")
DEPARTMENT_WEIGHT = Decimal("0.20")
SCORE_MIN = Decimal("0")
SCORE_MAX = Decimal("100")
CENT = Decimal("0.01")


class ScoringError(ValueError):
    pass


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize_scale_score(score):
    value = _to_decimal(score)
    if value is None or value < SCALE_MIN or value > SCALE_MAX:
        return None
    return (value - SCALE_MIN) / (SCALE_MAX - SCALE_MIN) * SCORE_MAX


def calculate_individual_score(review):
    total_weight = Decimal("0")
    weighted_sum = Decimal("0")
    answers = review.answers.select_related("question").filter(
        question__is_active=True
    )
    for answer in answers:
        question = answer.question
        if question.question_type != Question.QuestionType.SCALE:
            continue
        normalized = normalize_scale_score(answer.score)
        if normalized is None:
            continue
        weight = Decimal(question.weight)
        weighted_sum += normalized * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return weighted_sum / total_weight


def calculate_department_adjustment(department_score):
    value = _to_decimal(department_score)
    if value is None:
        return None
    return (value - DEPARTMENT_BASELINE) * DEPARTMENT_WEIGHT


def calculate_final_score(individual_score, department_adjustment):
    value = _to_decimal(individual_score)
    if value is None:
        return None
    adjustment = _to_decimal(department_adjustment) or Decimal("0")
    total = value + adjustment
    return max(SCORE_MIN, min(SCORE_MAX, total))


def calculate_and_store_final_score(review):
    individual_score = calculate_individual_score(review)
    if individual_score is None:
        raise ScoringError("no scorable answers for this review")
    performance = None
    if review.employee.department_id:
        performance = DepartmentPerformance.objects.filter(
            review_period=review.review_period,
            department_id=review.employee.department_id,
        ).first()
    if performance is None:
        raise ScoringError("department performance score is not entered")
    department_score = performance.performance_score
    adjustment = calculate_department_adjustment(department_score)
    final_score = calculate_final_score(individual_score, adjustment)
    stored, _ = FinalScore.objects.update_or_create(
        review=review,
        defaults={
            "individual_score": individual_score.quantize(CENT, rounding=ROUND_HALF_UP),
            "department_score": department_score.quantize(CENT, rounding=ROUND_HALF_UP),
            "department_adjustment": adjustment.quantize(CENT, rounding=ROUND_HALF_UP),
            "final_score": final_score.quantize(CENT, rounding=ROUND_HALF_UP),
            "calculated_at": timezone.now(),
        },
    )
    return stored
