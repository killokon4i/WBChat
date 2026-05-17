from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Department, Position, EmployeeStatusLog, EmployeeChangeLog

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    """Сериализатор подразделения"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    head_name = serializers.CharField(source='head.get_full_name', read_only=True)
    employee_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'description',
            'parent', 'parent_name', 'level', 'path',
            'head', 'head_name', 'is_active',
            'employee_count', 'children',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['level', 'path', 'created_at', 'updated_at']

    def get_employee_count(self, obj):
        return obj.employees.filter(is_active=True, is_archived=False).count()

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return DepartmentListSerializer(children, many=True).data


class DepartmentListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор для списков"""
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'level', 'employee_count']

    def get_employee_count(self, obj):
        return obj.employees.filter(is_active=True, is_archived=False).count()


class PositionSerializer(serializers.ModelSerializer):
    """Сериализатор должности"""
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Position
        fields = [
            'id', 'name', 'code', 'description',
            'department', 'department_name',
            'is_manager', 'grade_min', 'grade_max',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class EmployeeListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор сотрудника для списков"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'middle_name',
            'full_name',
            'department', 'department_name',
            'position', 'position_name',
            'status', 'avatar'
        ]

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор сотрудника"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    short_name = serializers.CharField(source='get_short_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    substitute_name = serializers.CharField(source='substitute.get_full_name', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    is_on_leave = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'middle_name',
            'full_name', 'short_name',
            'email', 'work_email', 'work_phone',
            'department', 'department_name',
            'position', 'position_name',
            'band', 'employee_category',
            'hire_date', 'birth_date',
            'manager', 'manager_name',
            'status', 'status_end_date',
            'substitute', 'substitute_name',
            'telegram', 'about',
            'avatar_url', 'is_on_leave',
            'show_birth_date', 'show_personal_phone',
        ]

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class EmployeeStatusLogSerializer(serializers.ModelSerializer):
    """Сериализатор журнала статусов"""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    substitute_name = serializers.CharField(source='substitute.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EmployeeStatusLog
        fields = [
            'id', 'employee', 'employee_name',
            'status', 'status_display',
            'start_date', 'end_date',
            'substitute', 'substitute_name',
            'note', 'created_at'
        ]
        read_only_fields = ['created_at']


class BirthdaySerializer(serializers.Serializer):
    """Сериализатор для дней рождения"""
    user = EmployeeListSerializer()
    date = serializers.DateField()
    days_until = serializers.IntegerField()
    age = serializers.IntegerField()

