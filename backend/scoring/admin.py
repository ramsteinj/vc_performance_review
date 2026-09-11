from django.contrib import admin

from .models import DepartmentPerformance, FinalScore


@admin.register(DepartmentPerformance)
class DepartmentPerformanceAdmin(admin.ModelAdmin):
    list_display = ("review_period", "department", "performance_score")
    list_filter = ("review_period",)


@admin.register(FinalScore)
class FinalScoreAdmin(admin.ModelAdmin):
    list_display = (
        "review",
        "individual_score",
        "department_score",
        "department_adjustment",
        "final_score",
        "calculated_at",
    )
