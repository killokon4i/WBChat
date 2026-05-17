from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmployeeProject


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'department', 'position', 'status', 'is_active']
    list_filter = ['is_active', 'is_archived', 'status', 'isModerator', 'is_hr', 'department']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'employee_id']
    raw_id_fields = ['manager', 'hr_partner', 'substitute', 'department', 'position']
    readonly_fields = ['hr_synced_at', 'archived_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('HR данные', {
            'fields': (
                'employee_id', 'middle_name', 'birth_date',
                'position', 'department', 'hire_date', 'termination_date',
                'work_phone', 'work_email', 'office_location',
                'band', 'employee_category',
                'manager', 'hr_partner',
                'hr_synced_at', 'hr_external_data',
            )
        }),
        ('Личные данные', {
            'fields': (
                'avatar', 'personal_phone', 'personal_email',
                'telegram', 'whatsapp',
                'about', 'skills',
            )
        }),
        ('Приватность', {
            'fields': (
                'show_birth_date', 'show_personal_phone', 'show_personal_email',
            )
        }),
        ('Статус и замещение', {
            'fields': (
                'status', 'status_end_date', 'substitute',
            )
        }),
        ('Роли портала', {
            'fields': (
                'isModerator', 'is_hr', 'is_admin_portal',
            )
        }),
        ('Архивация', {
            'fields': (
                'is_archived', 'archived_at', 'archived_reason',
            ),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Базовая информация', {
            'fields': ('first_name', 'last_name', 'email', 'department', 'position')
        }),
    )


@admin.register(EmployeeProject)
class EmployeeProjectAdmin(admin.ModelAdmin):
    list_display = ['employee', 'name', 'role', 'is_current', 'start_date', 'end_date', 'source']
    list_filter = ['is_current', 'source', 'start_date']
    search_fields = ['name', 'employee__username', 'employee__first_name', 'employee__last_name']
    raw_id_fields = ['employee']
    date_hierarchy = 'start_date'
