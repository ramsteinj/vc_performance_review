from rest_framework import viewsets

from accounts.permissions import IsAdminUserRole

from .models import Department
from .serializers import DepartmentSerializer
from .services import deactivate_department


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        return Department.objects.all().order_by("id")

    def perform_destroy(self, instance):
        deactivate_department(instance)
