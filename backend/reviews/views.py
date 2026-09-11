from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminUserRole, IsEmployeeOwner

from .models import Choice, Question, Review, ReviewPeriod
from .serializers import (
    AdminReviewCreateSerializer,
    AdminReviewSerializer,
    AnswerSerializer,
    AnswerUpsertListSerializer,
    ChoiceSerializer,
    EmployeeReviewDetailSerializer,
    EmployeeReviewSerializer,
    EvaluatorAssignSerializer,
    QuestionSerializer,
    ReviewPeriodSerializer,
)
from .services import (
    AnswerValidationError,
    EvaluatorValidationError,
    InvalidStatusTransition,
    QuestionLockedError,
    WeightTotalError,
    add_choice,
    assign_evaluators,
    change_status,
    create_question,
    create_review_period,
    deactivate_question,
    ensure_period_editable,
    get_or_create_review,
    get_progress,
    save_answer,
    submit_review,
    update_question,
    validate_evaluators,
)


class ReviewPeriodViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewPeriodSerializer
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        return ReviewPeriod.objects.all().order_by("id")

    def perform_create(self, serializer):
        data = serializer.validated_data
        try:
            period = create_review_period(
                name=data["name"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                description=data.get("description", ""),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        serializer.instance = period

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        period = self.get_object()
        new_status = request.data.get("status")
        if new_status not in ReviewPeriod.Status.values:
            raise ValidationError({"status": "invalid status"})
        try:
            change_status(period, new_status)
        except (InvalidStatusTransition, WeightTotalError) as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(period).data)


class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        return (
            Question.objects.select_related("review_period")
            .prefetch_related("choices")
            .order_by("id")
        )

    def perform_create(self, serializer):
        data = serializer.validated_data
        try:
            question = create_question(
                data["review_period"],
                text=data["text"],
                question_type=data["question_type"],
                weight=data["weight"],
                description=data.get("description", ""),
                display_order=data.get("display_order", 0),
                required=data.get("required", True),
            )
        except (QuestionLockedError, ValueError) as exc:
            raise ValidationError({"detail": str(exc)})
        serializer.instance = question

    def perform_update(self, serializer):
        if "review_period" in serializer.validated_data:
            raise ValidationError({"review_period": "review_period cannot be changed"})
        data = {
            key: value
            for key, value in serializer.validated_data.items()
            if key != "review_period"
        }
        try:
            update_question(serializer.instance, **data)
        except (QuestionLockedError, ValueError) as exc:
            raise ValidationError({"detail": str(exc)})

    def perform_destroy(self, instance):
        try:
            deactivate_question(instance)
        except QuestionLockedError as exc:
            raise ValidationError({"detail": str(exc)})

    @action(detail=True, methods=["get", "post"])
    def choices(self, request, pk=None):
        question = self.get_object()
        if request.method == "POST":
            serializer = ChoiceSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            try:
                choice = add_choice(
                    question,
                    text=data["text"],
                    display_order=data.get("display_order", 0),
                    score=data.get("score"),
                )
            except (QuestionLockedError, ValueError) as exc:
                return Response({"detail": str(exc)}, status=400)
            return Response(ChoiceSerializer(choice).data, status=201)
        return Response(ChoiceSerializer(question.choices.all(), many=True).data)

    @action(detail=True, methods=["delete"], url_path=r"choices/(?P<choice_id>\d+)")
    def choice(self, request, pk=None, choice_id=None):
        question = self.get_object()
        choice = get_object_or_404(Choice, id=choice_id, question=question)
        try:
            ensure_period_editable(question.review_period)
        except QuestionLockedError as exc:
            return Response({"detail": str(exc)}, status=400)
        choice.delete()
        return Response(status=204)


class AdminReviewViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = AdminReviewSerializer
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        return Review.objects.select_related(
            "review_period", "employee", "primary_evaluator", "secondary_evaluator"
        ).order_by("id")

    def create(self, request):
        serializer = AdminReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            validate_evaluators(
                data["employee"],
                data["primary_evaluator"],
                data.get("secondary_evaluator"),
            )
        except EvaluatorValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        review, created = get_or_create_review(
            data["review_period"],
            data["employee"],
            primary_evaluator=data["primary_evaluator"],
            secondary_evaluator=data.get("secondary_evaluator"),
        )
        if not created:
            return Response({"detail": "review already exists"}, status=409)
        return Response(AdminReviewSerializer(review).data, status=201)

    @action(detail=True, methods=["post"])
    def evaluators(self, request, pk=None):
        review = self.get_object()
        serializer = EvaluatorAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            assign_evaluators(
                review,
                primary_evaluator=data["primary_evaluator"],
                secondary_evaluator=data.get("secondary_evaluator"),
            )
        except EvaluatorValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(AdminReviewSerializer(review).data)


class EmployeeReviewViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsEmployeeOwner]

    def get_queryset(self):
        return (
            Review.objects.filter(employee=self.request.user)
            .select_related("review_period", "employee")
            .prefetch_related(
                "review_period__questions__choices",
                "answers__selected_choices",
            )
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EmployeeReviewDetailSerializer
        return EmployeeReviewSerializer

    @action(detail=False, methods=["get"])
    def my(self, request):
        reviews = self.get_queryset().order_by("id")
        serializer = EmployeeReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["put", "patch"])
    def answers(self, request, pk=None):
        review = self.get_object()
        serializer = AnswerUpsertListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                saved = []
                for item in serializer.validated_data["answers"]:
                    saved.append(
                        save_answer(
                            review,
                            item["question"],
                            answer_text=item.get("answer_text", ""),
                            score=item.get("score"),
                            choice_ids=item.get("choice_ids"),
                        )
                    )
        except AnswerValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        review.refresh_from_db()
        return Response(
            {
                "answers": AnswerSerializer(saved, many=True).data,
                "status": review.status,
                "progress": get_progress(review),
            }
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        review = self.get_object()
        try:
            submit_review(review)
        except AnswerValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(review).data)
