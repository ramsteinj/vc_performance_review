from django.db import models
from django.db.models import F, Q


class ReviewPeriod(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(start_date__lte=F("end_date")),
                name="reviewperiod_start_lte_end",
            ),
        ]

    def __str__(self):
        return self.name


class Question(models.Model):
    class QuestionType(models.TextChoices):
        TEXT = "TEXT", "Text"
        SINGLE_CHOICE = "SINGLE_CHOICE", "Single Choice"
        MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"
        SCALE = "SCALE", "Scale"

    review_period = models.ForeignKey(
        ReviewPeriod,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    description = models.TextField(blank=True)
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
    )
    weight = models.PositiveIntegerField()
    display_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=500)
    display_order = models.PositiveIntegerField(default=0)
    score = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return self.text
