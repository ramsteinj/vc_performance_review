from django.contrib import admin

from .models import ReviewPeriod


@admin.register(ReviewPeriod)
class ReviewPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("name",)
