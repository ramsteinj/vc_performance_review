from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

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
