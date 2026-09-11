from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUserRole
from reviews.services import filter_reviews

from .csv import write_reviews_csv
from .services import get_response_summary

UTF8_BOM = b"\xef\xbb\xbf"


class MonitoringSummaryView(APIView):
    permission_classes = [IsAdminUserRole]

    def get(self, request):
        summary = get_response_summary(
            review_period_id=request.query_params.get("review_period"),
            department_id=request.query_params.get("department"),
        )
        return Response(summary)


class ReviewCsvExportView(APIView):
    permission_classes = [IsAdminUserRole]

    def get(self, request):
        params = request.query_params
        queryset = filter_reviews(
            review_period_id=params.get("review_period"),
            department_id=params.get("department"),
            status=params.get("status"),
            employee_id=params.get("employee"),
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="reviews.csv"'
        response.write(UTF8_BOM)
        write_reviews_csv(response, queryset)
        return response
