import os

from django.contrib.auth import get_user_model

DEFAULT_ADMIN_PASSWORD = "admin1234!"


def ensure_default_admin():
    User = get_user_model()
    if User.objects.filter(employee_number="ADM001").exists():
        return False
    User.objects.create_user(
        username="ADM001",
        employee_number="ADM001",
        name="관리자",
        password=os.environ.get("DEFAULT_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
        role=User.Role.ADMIN,
    )
    return True
