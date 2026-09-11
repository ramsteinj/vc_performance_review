from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Department


class DepartmentModelTests(TestCase):
    def test_name_unique(self):
        Department.objects.create(name="개발팀")
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Department.objects.create(name="개발팀")

    def test_default_is_active(self):
        department = Department.objects.create(name="인사팀")
        self.assertTrue(department.is_active)
