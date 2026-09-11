from django.db.models import Count, Q

from reviews.models import Review
from reviews.services import filter_reviews


def get_response_summary(*, review_period_id=None, department_id=None):
    base = filter_reviews(
        review_period_id=review_period_id, department_id=department_id
    )
    total = base.count()
    not_started = base.filter(status=Review.Status.NOT_STARTED).count()
    in_progress = base.filter(status=Review.Status.IN_PROGRESS).count()
    submitted = base.filter(status=Review.Status.SUBMITTED).count()

    by_department = []
    groups = base.values(
        "employee__department__id", "employee__department__name"
    ).annotate(
        group_total=Count("id"),
        group_submitted=Count(
            "id", filter=Q(status=Review.Status.SUBMITTED)
        ),
    ).order_by("employee__department__name", "employee__department__id")
    for group in groups:
        group_total = group["group_total"]
        group_submitted = group["group_submitted"]
        by_department.append(
            {
                "department_id": group["employee__department__id"],
                "department": group["employee__department__name"],
                "total": group_total,
                "submitted": group_submitted,
                "response_rate": _rate(group_submitted, group_total),
            }
        )

    return {
        "total": total,
        "not_started": not_started,
        "in_progress": in_progress,
        "submitted": submitted,
        "response_rate": _rate(submitted, total),
        "by_department": by_department,
    }


def _rate(part, whole):
    if not whole:
        return 0.0
    return round(part * 100 / whole, 1)
