import csv
from decimal import Decimal

from reviews.models import Question
from scoring.services import normalize_scale_score


def write_reviews_csv(response, queryset):
    writer = csv.writer(response)
    reviews = list(
        queryset.select_related(
            "review_period",
            "employee__department",
            "primary_evaluator",
            "secondary_evaluator",
            "final_score",
        ).prefetch_related("answers__selected_choices")
    )
    period_ids = {review.review_period_id for review in reviews}
    questions = list(
        Question.objects.filter(review_period_id__in=period_ids, is_active=True)
        .select_related("review_period")
        .order_by("review_period_id", "display_order", "id")
    )
    labels = [f"[{q.review_period.name}] {q.text}" for q in questions]

    writer.writerow(
        ["평가 기간", "부서", "사번", "이름", "상태", "1차 평가자", "2차 평가자"]
        + [f"답변: {label}" for label in labels]
        + [f"점수: {label}" for label in labels]
        + ["개인 점수", "부서 점수", "부서 조정점수", "최종 점수", "제출일시"]
    )

    for review in reviews:
        answers = {answer.question_id: answer for answer in review.answers.all()}
        final_score = getattr(review, "final_score", None)
        row = [
            review.review_period.name,
            review.employee.department.name if review.employee.department else "",
            review.employee.employee_number,
            review.employee.name,
            review.status,
            review.primary_evaluator.name if review.primary_evaluator_id else "",
            review.secondary_evaluator.name if review.secondary_evaluator_id else "",
        ]
        row += [_answer_display(question, answers.get(question.id)) for question in questions]
        row += [_score_display(question, answers.get(question.id)) for question in questions]
        row += [
            final_score.individual_score if final_score else "",
            final_score.department_score if final_score else "",
            final_score.department_adjustment if final_score else "",
            final_score.final_score if final_score else "",
            (
                review.submitted_at.strftime("%Y-%m-%d %H:%M")
                if review.submitted_at
                else ""
            ),
        ]
        writer.writerow(row)


def _answer_display(question, answer):
    if answer is None:
        return ""
    if question.question_type in (
        Question.QuestionType.SINGLE_CHOICE,
        Question.QuestionType.MULTIPLE_CHOICE,
    ):
        return ", ".join(
            choice.text for choice in answer.selected_choices.all()
        )
    if question.question_type == Question.QuestionType.SCALE:
        return str(answer.score) if answer.score is not None else ""
    return answer.answer_text


def _score_display(question, answer):
    if answer is None or question.question_type != Question.QuestionType.SCALE:
        return ""
    normalized = normalize_scale_score(answer.score)
    if normalized is None:
        return ""
    return str(normalized.quantize(Decimal("0.01")))
