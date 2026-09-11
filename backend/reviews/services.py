from django.db import transaction

from .models import ReviewPeriod


class InvalidStatusTransition(ValueError):
    pass


ALLOWED_TRANSITIONS = {
    ReviewPeriod.Status.DRAFT: {ReviewPeriod.Status.OPEN},
    ReviewPeriod.Status.OPEN: {ReviewPeriod.Status.CLOSED},
    ReviewPeriod.Status.CLOSED: set(),
}


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
    review_period.status = new_status
    review_period.save(update_fields=["status", "updated_at"])
    return review_period
