"""
Celery задачи для синхронизации с внешними системами.
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_hr_provider():
    """Получить HR провайдер на основе настроек"""
    provider_path = getattr(settings, 'INTEGRATIONS', {}).get(
        'HR_PROVIDER',
        'integrations.hr.mock.MockHRProvider'
    )
    
    module_path, class_name = provider_path.rsplit('.', 1)
    module = __import__(module_path, fromlist=[class_name])
    provider_class = getattr(module, class_name)
    
    return provider_class()


@shared_task
def sync_employees_from_hr():
    """
    Периодическая синхронизация сотрудников из HR-системы.
    Запускается по расписанию (например, каждый час).
    """
    from django.contrib.auth import get_user_model
    from org.models import Department, Position
    
    User = get_user_model()
    provider = get_hr_provider()
    
    if not provider.check_connection():
        logger.error("Cannot connect to HR system")
        return {'status': 'error', 'message': 'Connection failed'}
    
    # Получаем обновлённых сотрудников
    # За последние 2 часа для надёжности
    last_sync = timezone.now() - timezone.timedelta(hours=2)
    employees = provider.get_all_employees(updated_since=last_sync)
    
    synced = 0
    errors = 0
    
    for emp_data in employees:
        try:
            user, created = User.objects.update_or_create(
                employee_id=emp_data['employee_id'],
                defaults={
                    'first_name': emp_data.get('first_name', ''),
                    'last_name': emp_data.get('last_name', ''),
                    'middle_name': emp_data.get('middle_name', ''),
                    'work_email': emp_data.get('work_email', ''),
                    'work_phone': emp_data.get('work_phone', ''),
                    'band': emp_data.get('band', ''),
                    'hr_synced_at': timezone.now(),
                }
            )
            
            # Обновляем должность
            if emp_data.get('position_code'):
                position = Position.objects.filter(code=emp_data['position_code']).first()
                if position:
                    user.position = position
                    user.save(update_fields=['position'])
            
            # Обновляем подразделение
            if emp_data.get('department_code'):
                department = Department.objects.filter(code=emp_data['department_code']).first()
                if department:
                    user.department = department
                    user.save(update_fields=['department'])
            
            synced += 1
            
        except Exception as e:
            logger.error(f"Error syncing employee {emp_data.get('employee_id')}: {e}")
            errors += 1
    
    logger.info(f"HR sync completed: {synced} synced, {errors} errors")
    return {'status': 'completed', 'synced': synced, 'errors': errors}


@shared_task
def sync_departments_from_hr():
    """
    Синхронизация подразделений из HR-системы.
    """
    from org.models import Department
    
    provider = get_hr_provider()
    
    if not provider.check_connection():
        logger.error("Cannot connect to HR system")
        return {'status': 'error', 'message': 'Connection failed'}
    
    departments = provider.get_departments()
    synced = 0
    
    for dept_data in departments:
        try:
            # Сначала находим родителя
            parent = None
            if dept_data.get('parent_code'):
                parent = Department.objects.filter(code=dept_data['parent_code']).first()
            
            dept, created = Department.objects.update_or_create(
                code=dept_data['code'],
                defaults={
                    'name': dept_data['name'],
                    'parent': parent,
                    'external_id': dept_data.get('external_id', dept_data['code']),
                    'is_active': dept_data.get('is_active', True),
                }
            )
            synced += 1
            
        except Exception as e:
            logger.error(f"Error syncing department {dept_data.get('code')}: {e}")
    
    logger.info(f"Department sync completed: {synced} synced")
    return {'status': 'completed', 'synced': synced}


@shared_task
def sync_positions_from_hr():
    """
    Синхронизация должностей из HR-системы.
    """
    from org.models import Position
    
    provider = get_hr_provider()
    
    if not provider.check_connection():
        logger.error("Cannot connect to HR system")
        return {'status': 'error', 'message': 'Connection failed'}
    
    positions = provider.get_positions()
    synced = 0
    
    for pos_data in positions:
        try:
            pos, created = Position.objects.update_or_create(
                code=pos_data['code'],
                defaults={
                    'name': pos_data['name'],
                    'is_manager': pos_data.get('is_manager', False),
                    'external_id': pos_data.get('external_id', pos_data['code']),
                    'is_active': pos_data.get('is_active', True),
                }
            )
            synced += 1
            
        except Exception as e:
            logger.error(f"Error syncing position {pos_data.get('code')}: {e}")
    
    logger.info(f"Position sync completed: {synced} synced")
    return {'status': 'completed', 'synced': synced}


@shared_task
def archive_terminated_employees():
    """
    Архивирование уволенных сотрудников.
    Проверяет статусы в HR и архивирует уволенных.
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    provider = get_hr_provider()
    
    if not provider.check_connection():
        logger.error("Cannot connect to HR system")
        return {'status': 'error', 'message': 'Connection failed'}
    
    archived = 0
    
    # Проверяем только активных сотрудников с employee_id
    active_users = User.objects.filter(
        is_active=True,
        is_archived=False,
        employee_id__isnull=False
    )
    
    for user in active_users:
        status_data = provider.get_employee_status(user.employee_id)
        
        if status_data and status_data.get('status') == 'terminated':
            user.archive(reason='Уволен (синхронизация HR)')
            archived += 1
            logger.info(f"Archived terminated employee: {user.employee_id}")
    
    logger.info(f"Archive task completed: {archived} archived")
    return {'status': 'completed', 'archived': archived}


@shared_task
def update_employee_statuses():
    """
    Обновление статусов сотрудников (отпуск, больничный и т.д.).
    """
    from django.contrib.auth import get_user_model
    from org.models import EmployeeStatusLog
    
    User = get_user_model()
    provider = get_hr_provider()
    
    if not provider.check_connection():
        logger.error("Cannot connect to HR system")
        return {'status': 'error', 'message': 'Connection failed'}
    
    updated = 0
    
    active_users = User.objects.filter(
        is_active=True,
        is_archived=False,
        employee_id__isnull=False
    )
    
    for user in active_users:
        status_data = provider.get_employee_status(user.employee_id)
        
        if status_data and status_data.get('status') != user.status:
            old_status = user.status
            user.status = status_data['status']
            
            if status_data.get('end_date'):
                from datetime import datetime
                user.status_end_date = datetime.fromisoformat(status_data['end_date']).date()
            
            user.save(update_fields=['status', 'status_end_date'])
            
            # Логируем изменение
            EmployeeStatusLog.objects.create(
                employee=user,
                status=status_data['status'],
                start_date=timezone.now().date(),
                end_date=user.status_end_date,
            )
            
            updated += 1
    
    logger.info(f"Status update completed: {updated} updated")
    return {'status': 'completed', 'updated': updated}


