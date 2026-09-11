from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from rest_framework.test import APITestCase

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


class DepartmentAdminApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADM001",
            employee_number="ADM001",
            name="관리자",
            password="test-password-123!",
            role=User.Role.ADMIN,
        )
        self.employee = User.objects.create_user(
            username="EMP001",
            employee_number="EMP001",
            name="홍길동",
            password="test-password-123!",
        )

    def test_employee_cannot_access_admin_api(self):
        self.client.force_login(self.employee)
        response = self.client.get("/api/admin/departments/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_department(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/departments/",
            {"name": "개발팀", "description": "제품 개발"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Department.objects.filter(name="개발팀").exists())

    def test_duplicate_name_rejected(self):
        Department.objects.create(name="개발팀")
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/admin/departments/", {"name": "개발팀"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_update_department(self):
        department = Department.objects.create(name="개발팀")
        self.client.force_login(self.admin)
        response = self.client.patch(
            f"/api/admin/departments/{department.id}/",
            {"description": "수정된 설명"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        department.refresh_from_db()
        self.assertEqual(department.description, "수정된 설명")

    def test_destroy_soft_deletes(self):
        department = Department.objects.create(name="개발팀")
        self.client.force_login(self.admin)
        response = self.client.delete(f"/api/admin/departments/{department.id}/")
        self.assertEqual(response.status_code, 204)
        department.refresh_from_db()
        self.assertFalse(department.is_active)
