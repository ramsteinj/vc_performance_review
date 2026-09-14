from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from departments.models import Department

User = get_user_model()


class UserModelTests(TestCase):
    def create_user(self, **overrides):
        data = {
            "username": "EMP001",
            "employee_number": "EMP001",
            "name": "홍길동",
            "password": "test-password-123!",
        }
        data.update(overrides)
        return User.objects.create_user(**data)

    def test_auth_user_model_setting(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_default_role_is_employee(self):
        user = self.create_user()
        self.assertEqual(user.role, User.Role.EMPLOYEE)

    def test_admin_role(self):
        user = self.create_user(
            employee_number="ADM001",
            username="ADM001",
            role=User.Role.ADMIN,
        )
        self.assertEqual(user.role, User.Role.ADMIN)

    def test_employee_number_unique(self):
        self.create_user()
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.create_user(username="EMP999")

    def test_password_is_hashed(self):
        user = self.create_user()
        self.assertNotEqual(user.password, "test-password-123!")
        self.assertTrue(user.check_password("test-password-123!"))

    def test_inactive_user_flag(self):
        user = self.create_user()
        user.is_active = False
        user.save()
        self.assertFalse(User.objects.get(employee_number="EMP001").is_active)


class AuthApiTests(APITestCase):
    def create_api_user(self, employee_number="EMP001", **overrides):
        data = {
            "username": employee_number,
            "employee_number": employee_number,
            "name": "홍길동",
            "password": "test-password-123!",
        }
        data.update(overrides)
        return User.objects.create_user(**data)

    def login_payload(self, **overrides):
        data = {
            "name": "홍길동",
            "employee_number": "EMP001",
            "password": "test-password-123!",
        }
        data.update(overrides)
        return data

    def test_login_success(self):
        self.create_api_user()
        response = self.client.post("/api/auth/login/", self.login_payload(), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["employee_number"], "EMP001")
        self.assertNotIn("password", response.data)

    def test_login_rejects_wrong_name(self):
        self.create_api_user()
        response = self.client.post(
            "/api/auth/login/", self.login_payload(name="다른이름"), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_login_rejects_wrong_password(self):
        self.create_api_user()
        response = self.client.post(
            "/api/auth/login/", self.login_payload(password="wrong-password"), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_login_rejects_unknown_employee_number(self):
        response = self.client.post("/api/auth/login/", self.login_payload(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_inactive_user_cannot_login(self):
        self.create_api_user()
        User.objects.filter(employee_number="EMP001").update(is_active=False)
        response = self.client.post("/api/auth/login/", self.login_payload(), format="json")
        self.assertEqual(response.status_code, 403)

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 403)

    def test_me_returns_current_user(self):
        department = Department.objects.create(name="개발팀")
        self.create_api_user(department=department)
        self.client.force_login(User.objects.get(employee_number="EMP001"))
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["department_detail"], {"id": department.id, "name": "개발팀"}
        )

    def test_logout_ends_session(self):
        self.create_api_user()
        self.client.force_login(User.objects.get(employee_number="EMP001"))
        response = self.client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 403)


class PasswordChangeApiTests(APITestCase):
    def create_user(self, employee_number="EMP001", **overrides):
        data = {
            "username": employee_number,
            "employee_number": employee_number,
            "name": "홍길동",
            "password": "test-password-123!",
        }
        data.update(overrides)
        return User.objects.create_user(**data)

    def test_change_password_success(self):
        user = self.create_user()
        self.client.force_login(user)
        response = self.client.post(
            "/api/auth/password/change/",
            {
                "current_password": "test-password-123!",
                "new_password": "new-password-456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        user.refresh_from_db()
        self.assertTrue(user.check_password("new-password-456!"))
        self.assertFalse(user.check_password("test-password-123!"))
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_rejects_wrong_current_password(self):
        user = self.create_user()
        self.client.force_login(user)
        response = self.client.post(
            "/api/auth/password/change/",
            {
                "current_password": "wrong-password",
                "new_password": "new-password-456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password("test-password-123!"))

    def test_rejects_short_password(self):
        user = self.create_user()
        self.client.force_login(user)
        response = self.client.post(
            "/api/auth/password/change/",
            {"current_password": "test-password-123!", "new_password": "short1!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_numeric_only_password(self):
        user = self.create_user()
        self.client.force_login(user)
        response = self.client.post(
            "/api/auth/password/change/",
            {"current_password": "test-password-123!", "new_password": "12345678"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_requires_authentication(self):
        response = self.client.post(
            "/api/auth/password/change/",
            {"current_password": "test-password-123!", "new_password": "new-password-456!"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class UserAdminApiTests(APITestCase):
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
        response = self.client.get("/api/admin/users/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_users(self):
        self.client.force_login(self.admin)
        response = self.client.get("/api/admin/users/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_admin_can_create_user(self):
        self.client.force_login(self.admin)
        payload = {
            "employee_number": "EMP002",
            "name": "새 직원",
            "role": "EMPLOYEE",
            "password": "new-password-123!",
        }
        response = self.client.post("/api/admin/users/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)
        created = User.objects.get(employee_number="EMP002")
        self.assertEqual(created.username, "EMP002")
        self.assertTrue(created.check_password("new-password-123!"))

    def test_created_user_can_login(self):
        self.client.force_login(self.admin)
        self.client.post(
            "/api/admin/users/",
            {
                "employee_number": "EMP002",
                "name": "새 직원",
                "role": "EMPLOYEE",
                "password": "new-password-123!",
            },
            format="json",
        )
        self.client.logout()
        response = self.client.post(
            "/api/auth/login/",
            {
                "name": "새 직원",
                "employee_number": "EMP002",
                "password": "new-password-123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_deactivate_user(self):
        self.client.force_login(self.admin)
        response = self.client.patch(
            f"/api/admin/users/{self.employee.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.client.logout()
        response = self.client.post(
            "/api/auth/login/",
            {
                "name": "홍길동",
                "employee_number": "EMP001",
                "password": "test-password-123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_destroy_soft_deletes_user(self):
        self.client.force_login(self.admin)
        response = self.client.delete(f"/api/admin/users/{self.employee.id}/")
        self.assertEqual(response.status_code, 204)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
