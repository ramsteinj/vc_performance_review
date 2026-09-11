from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from .models import Department
from .services import activate_department, deactivate_department

User = get_user_model()


class DepartmentModelTests(TestCase):
    def test_name_unique(self):
        Department.objects.create(name="개발팀")
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Department.objects.create(name="개발팀")

    def test_default_is_active(self):
        department = Department.objects.create(name="인사팀")
        self.assertTrue(department.is_active)


class DepartmentServiceTests(TestCase):
    def test_deactivate_and_activate(self):
        department = Department.objects.create(name="개발팀")
        deactivate_department(department)
        department.refresh_from_db()
        self.assertFalse(department.is_active)
        activate_department(department)
        department.refresh_from_db()
        self.assertTrue(department.is_active)


class DepartmentUserRelationTests(TestCase):
    def test_department_delete_protected_by_user(self):
        department = Department.objects.create(name="개발팀")
        User.objects.create_user(
            username="EMP001",
            employee_number="EMP001",
            name="홍길동",
            password="test-password-123!",
            department=department,
        )
        with self.assertRaises(ProtectedError):
            department.delete()
