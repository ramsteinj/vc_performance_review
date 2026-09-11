from rest_framework import serializers

from .models import Choice, Question, ReviewPeriod


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "text", "display_order", "score")


class QuestionSerializer(serializers.ModelSerializer):
    review_period = serializers.PrimaryKeyRelatedField(
        queryset=ReviewPeriod.objects.all()
    )
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "review_period",
            "text",
            "description",
            "question_type",
            "weight",
            "display_order",
            "required",
            "is_active",
            "choices",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class ReviewPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewPeriod
        fields = (
            "id",
            "name",
            "description",
            "start_date",
            "end_date",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("status", "created_at", "updated_at")

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date", getattr(self.instance, "start_date", None)
        )
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "start_date must be on or before end_date"
            )
        return attrs
