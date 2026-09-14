from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from departments.models import Department

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    name = serializers.CharField()
    employee_number = serializers.CharField()
    password = serializers.CharField()


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("current password is incorrect")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class UserSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )
    department_detail = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "employee_number",
            "name",
            "role",
            "department",
            "department_detail",
            "is_active",
            "password",
        )

    def validate_department(self, value):
        if value is not None and not value.is_active:
            raise serializers.ValidationError(
                "inactive department cannot be assigned"
            )
        return value

    def get_department_detail(self, obj):
        if obj.department_id is None:
            return None
        return {"id": obj.department_id, "name": obj.department.name}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "password is required"})
        validated_data.setdefault("username", validated_data.get("employee_number"))
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
