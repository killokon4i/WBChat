from django.contrib import admin
from .models import Department, Position, EmployeeStatusLog, EmployeeChangeLog


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'parent', 'level', 'head', 'is_active']
    list_filter = ['is_active', 'level']
    search_fields = ['name', 'code']
    raw_id_fields = ['parent', 'head']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'is_manager']
    list_filter = ['is_manager', 'department']
    search_fields = ['name', 'code']


@admin.register(EmployeeStatusLog)
class EmployeeStatusLogAdmin(admin.ModelAdmin):
    list_display = ['employee', 'status', 'start_date', 'end_date', 'created_at']
    list_filter = ['status', 'start_date']
    search_fields = ['employee__username', 'employee__first_name', 'employee__last_name']
    raw_id_fields = ['employee', 'substitute', 'created_by']


@admin.register(EmployeeChangeLog)
class EmployeeChangeLogAdmin(admin.ModelAdmin):
    list_display = ['employee', 'field_name', 'changed_by', 'changed_at', 'source']
    list_filter = ['field_name', 'source', 'changed_at']
    search_fields = ['employee__username', 'field_name']
    raw_id_fields = ['employee', 'changed_by']
    readonly_fields = ['changed_at']


