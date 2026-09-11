from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Answer, Choice, Question, Review, ReviewPeriod
from .services import get_progress

User = get_user_model()


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


class UserBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    employee_number = serializers.CharField()
    name = serializers.CharField()


class ReviewPeriodBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewPeriod
        fields = ("id", "name", "start_date", "end_date", "status")


class AnswerSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(read_only=True)
    selected_choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Answer
        fields = (
            "question",
            "answer_text",
            "score",
            "selected_choices",
            "updated_at",
        )


class EmployeeQuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "text",
            "description",
            "question_type",
            "weight",
            "display_order",
            "required",
            "choices",
        )


class EmployeeReviewSerializer(serializers.ModelSerializer):
    review_period = ReviewPeriodBriefSerializer(read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "review_period", "status", "progress", "submitted_at")

    def get_progress(self, obj):
        return get_progress(obj)


class EmployeeReviewDetailSerializer(EmployeeReviewSerializer):
    questions = serializers.SerializerMethodField()
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta(EmployeeReviewSerializer.Meta):
        fields = EmployeeReviewSerializer.Meta.fields + ("questions", "answers")

    def get_questions(self, obj):
        active_questions = obj.review_period.questions.filter(is_active=True)
        return EmployeeQuestionSerializer(active_questions, many=True).data


class AdminReviewSerializer(serializers.ModelSerializer):
    review_period = ReviewPeriodBriefSerializer(read_only=True)
    employee = UserBriefSerializer(read_only=True)
    primary_evaluator = UserBriefSerializer(read_only=True)
    secondary_evaluator = UserBriefSerializer(read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "review_period",
            "employee",
            "primary_evaluator",
            "secondary_evaluator",
            "status",
            "submitted_at",
        )


class EvaluatorAssignSerializer(serializers.Serializer):
    primary_evaluator = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )
    secondary_evaluator = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )


class AdminReviewCreateSerializer(EvaluatorAssignSerializer):
    review_period = serializers.PrimaryKeyRelatedField(
        queryset=ReviewPeriod.objects.all()
    )
    employee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )


class AnswerUpsertSerializer(serializers.Serializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    answer_text = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    score = serializers.IntegerField(required=False, allow_null=True, default=None)
    choice_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True,
        default=None,
    )


class AnswerUpsertListSerializer(serializers.Serializer):
    answers = AnswerUpsertSerializer(many=True, min_length=1)
