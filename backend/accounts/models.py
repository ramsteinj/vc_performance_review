from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        ADMIN = "ADMIN", "Admin"

    employee_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
