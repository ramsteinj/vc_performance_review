from django.contrib import admin

from .models import Answer, Review, ReviewPeriod


@admin.register(ReviewPeriod)
class ReviewPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "review_period",
        "employee",
        "status",
        "primary_evaluator",
        "submitted_at",
    )
    list_filter = ("status",)
    search_fields = ("employee__employee_number", "employee__name")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("review", "question", "updated_at")
