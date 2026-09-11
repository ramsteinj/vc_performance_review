from django.contrib.auth import get_user_model
from rest_framework import serializers

from departments.models import Department
from reviews.models import ReviewPeriod

from .models import DepartmentPerformance, FinalScore

User = get_user_model()


class DepartmentPerformanceSerializer(serializers.ModelSerializer):
    review_period = serializers.PrimaryKeyRelatedField(
        queryset=ReviewPeriod.objects.all()
    )
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    performance_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100
    )

    class Meta:
        model = DepartmentPerformance
        fields = (
            "id",
            "review_period",
            "department",
            "performance_score",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        review_period = attrs.get(
            "review_period", getattr(self.instance, "review_period", None)
        )
        department = attrs.get(
            "department", getattr(self.instance, "department", None)
        )
        exists = DepartmentPerformance.objects.filter(
            review_period=review_period, department=department
        ).exclude(pk=getattr(self.instance, "pk", None))
        if exists.exists():
            raise serializers.ValidationError(
                "department performance already exists for this period"
            )
        return attrs


class FinalScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalScore
        fields = (
            "individual_score",
            "department_score",
            "department_adjustment",
            "final_score",
            "calculated_at",
        )
