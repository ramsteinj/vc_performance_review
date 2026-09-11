from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import UserViewSet
from departments.views import DepartmentViewSet
from reviews.views import (
    AdminReviewViewSet,
    EmployeeReviewViewSet,
    QuestionViewSet,
    ReviewPeriodViewSet,
)
from scoring.views import DepartmentPerformanceViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("departments", DepartmentViewSet, basename="departments")
router.register("review-periods", ReviewPeriodViewSet, basename="review-periods")
router.register("questions", QuestionViewSet, basename="questions")
router.register("reviews", AdminReviewViewSet, basename="admin-reviews")
router.register(
    "department-performances",
    DepartmentPerformanceViewSet,
    basename="department-performances",
)

employee_router = DefaultRouter()
employee_router.register("reviews", EmployeeReviewViewSet, basename="reviews")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/admin/monitoring/", include("monitoring.urls")),
    path("api/admin/", include(router.urls)),
    path("api/", include(employee_router.urls)),
]
