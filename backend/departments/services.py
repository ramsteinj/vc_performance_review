from .models import Department


def activate_department(department):
    department.is_active = True
    department.save(update_fields=["is_active", "updated_at"])
    return department


def deactivate_department(department):
    department.is_active = False
    department.save(update_fields=["is_active", "updated_at"])
    return department
