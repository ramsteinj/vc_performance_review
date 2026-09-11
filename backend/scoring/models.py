from django.db import models

from departments.models import Department
from reviews.models import Review, ReviewPeriod


class DepartmentPerformance(models.Model):
    review_period = models.ForeignKey(
        ReviewPeriod,
        on_delete=models.CASCADE,
        related_name="department_performances",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="department_performances",
    )
    performance_score = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review_period", "department"],
                name="unique_department_performance_per_period",
            ),
        ]

    def __str__(self):
        return f"{self.review_period} / {self.department}"


class FinalScore(models.Model):
    review = models.OneToOneField(
        Review,
        on_delete=models.CASCADE,
        related_name="final_score",
    )
    individual_score = models.DecimalField(max_digits=5, decimal_places=2)
    department_score = models.DecimalField(max_digits=5, decimal_places=2)
    department_adjustment = models.DecimalField(max_digits=5, decimal_places=2)
    final_score = models.DecimalField(max_digits=5, decimal_places=2)
    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.review} → {self.final_score}"
