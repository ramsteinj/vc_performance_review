from django.conf import settings
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


class Review(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        SUBMITTED = "SUBMITTED", "Submitted"

    review_period = models.ForeignKey(
        ReviewPeriod,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    primary_evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="primary_reviews",
    )
    secondary_evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="secondary_reviews",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review_period", "employee"],
                name="unique_review_per_period_and_employee",
            ),
        ]

    def __str__(self):
        return f"{self.review_period} / {self.employee}"


class Answer(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="answers",
    )
    answer_text = models.TextField(blank=True)
    score = models.IntegerField(null=True, blank=True)
    selected_choices = models.ManyToManyField(
        Choice,
        blank=True,
        related_name="answers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review", "question"],
                name="unique_answer_per_review_and_question",
            ),
        ]

    def __str__(self):
        return f"{self.review} / {self.question}"
