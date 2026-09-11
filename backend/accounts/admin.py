from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("employee_number", "name", "role", "department", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("employee_number", "name")
