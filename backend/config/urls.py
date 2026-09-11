from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import UserViewSet
from departments.views import DepartmentViewSet
from reviews.views import QuestionViewSet, ReviewPeriodViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("departments", DepartmentViewSet, basename="departments")
router.register("review-periods", ReviewPeriodViewSet, basename="review-periods")
router.register("questions", QuestionViewSet, basename="questions")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/admin/", include(router.urls)),
]
