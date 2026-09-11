from rest_framework import viewsets

from accounts.permissions import IsAdminUserRole

from .models import DepartmentPerformance
from .serializers import DepartmentPerformanceSerializer


class DepartmentPerformanceViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentPerformanceSerializer
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        return DepartmentPerformance.objects.select_related(
            "review_period", "department"
        ).order_by("id")
