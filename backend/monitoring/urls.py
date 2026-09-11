from django.urls import path

from .views import MonitoringSummaryView, ReviewCsvExportView

urlpatterns = [
    path("summary/", MonitoringSummaryView.as_view(), name="monitoring-summary"),
    path("export/", ReviewCsvExportView.as_view(), name="monitoring-export"),
]
