from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .models import Department, Position
from .services import DirectoryService, BirthdayService

User = get_user_model()
directory_service = DirectoryService()
birthday_service = BirthdayService()


@login_required
def directory(request):
    """Главная страница справочника сотрудников"""
    query = request.GET.get('q', '')
    department_id = request.GET.get('department')
    
    # Получаем дерево подразделений
    departments = directory_service.get_department_tree()
    
    # Поиск сотрудников
    if query or department_id:
        employees = directory_service.search_employees(
            query=query,
            department_id=int(department_id) if department_id else None
        )
    else:
        employees = User.objects.filter(
            is_active=True, 
            is_archived=False
        ).select_related('department', 'position').order_by('last_name', 'first_name')[:50]
    
    # Ближайшие дни рождения
    upcoming_birthdays = birthday_service.get_upcoming_birthdays(days=14)[:5]
    
    return render(request, 'org/directory.html', {
        'departments': departments,
        'employees': employees,
        'query': query,
        'selected_department': int(department_id) if department_id else None,
        'upcoming_birthdays': upcoming_birthdays,
    })


@login_required
def employee_card(request, user_id):
    """Карточка сотрудника"""
    employee = get_object_or_404(
        User.objects.select_related('department', 'position', 'manager', 'substitute'),
        id=user_id
    )

    subordinates = directory_service.get_subordinates(user_id, direct_only=True)

    is_admin = (request.user.is_superuser
                or getattr(request.user, 'isModerator', False)
                or getattr(request.user, 'is_admin_portal', False))

    embed = request.GET.get('embed', '').lower() in ('1', 'true', 'yes')
    from_chat = request.GET.get('from_chat', '').strip()
    hide_chat_button = False

    if embed and from_chat:
        try:
            from chat.models import Conversation
            conv = Conversation.objects.filter(
                pk=int(from_chat),
                participants=request.user,
            ).first()
            if conv and conv.type == 'direct':
                other_ids = list(
                    conv.participants.exclude(pk=request.user.pk).values_list('pk', flat=True)
                )
                if len(other_ids) == 1 and other_ids[0] == employee.id:
                    hide_chat_button = True
        except (ValueError, TypeError):
            pass

    template = 'org/employee_card_embed.html' if embed else 'org/employee_card.html'
    return render(request, template, {
        'employee': employee,
        'subordinates': subordinates,
        'is_admin': is_admin,
        'from_chat': from_chat,
        'hide_chat_button': hide_chat_button,
    })


@login_required
def unban_comments(request, user_id):
    """Снять блокировку комментариев с пользователя."""
    if not (request.user.is_superuser
            or getattr(request.user, 'isModerator', False)
            or getattr(request.user, 'is_admin_portal', False)):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Нет прав')
    
    from django.contrib import messages
    employee = get_object_or_404(User, id=user_id)
    employee.is_comments_banned = False
    employee.comment_warnings = 0
    employee.comments_banned_at = None
    employee.save(update_fields=['is_comments_banned', 'comment_warnings', 'comments_banned_at'])
    
    messages.success(request, f'Блокировка комментариев снята с {employee.get_full_name() or employee.username}.')
    return redirect('employee_card', user_id=user_id)


@login_required
def department_view(request, department_id):
    """Страница подразделения"""
    department = get_object_or_404(Department, id=department_id)
    
    # Получаем сотрудников
    employees = directory_service.get_department_employees(department_id, include_children=False)
    
    # Дочерние подразделения
    children = Department.objects.filter(parent=department, is_active=True)
    
    # Путь к корню (хлебные крошки)
    ancestors = department.get_ancestors()
    
    return render(request, 'org/department.html', {
        'department': department,
        'employees': employees,
        'children': children,
        'ancestors': ancestors,
    })


@login_required
def org_tree_api(request):
    """API для получения дерева оргструктуры"""
    root_id = request.GET.get('root')
    
    departments = directory_service.get_department_tree(
        root_id=int(root_id) if root_id else None
    )
    
    data = []
    for dept in departments:
        data.append({
            'id': dept.id,
            'name': dept.name,
            'code': dept.code,
            'parent_id': dept.parent_id,
            'level': dept.level,
            'employee_count': dept.employee_count,
            'head': {
                'id': dept.head.id,
                'name': dept.head.get_full_name(),
            } if dept.head else None,
        })
    
    return JsonResponse({'departments': data})


@login_required
def search_employees_api(request):
    """API для поиска сотрудников"""
    query = request.GET.get('q', '')
    department_id = request.GET.get('department')
    limit = int(request.GET.get('limit', 20))
    
    employees = directory_service.search_employees(
        query=query,
        department_id=int(department_id) if department_id else None,
        limit=limit
    )
    
    data = []
    for emp in employees:
        data.append({
            'id': emp.id,
            'username': emp.username,
            'full_name': emp.get_full_name() or emp.username,
            'has_avatar': emp.has_avatar,
            'avatar': emp.avatar.url if emp.has_avatar else None,
            'avatar_initials': emp.get_avatar_initials(),
            'position': emp.position.name if emp.position else None,
            'department': emp.department.name if emp.department else None,
            'status': emp.status,
        })
    
    return JsonResponse({'employees': data})


@login_required
def birthdays_api(request):
    """API для получения дней рождения"""
    days = int(request.GET.get('days', 14))
    department_id = request.GET.get('department')
    
    birthdays = birthday_service.get_upcoming_birthdays(
        days=days,
        department_id=int(department_id) if department_id else None
    )
    
    data = []
    for b in birthdays:
        user = b['user']
        data.append({
            'id': user.id,
            'full_name': user.get_full_name() or user.username,
            'avatar': user.avatar.url if user.avatar else None,
            'date': b['date'].isoformat(),
            'days_until': b['days_until'],
            'age': b['age'],
            'department': user.department.name if user.department else None,
        })
    
    return JsonResponse({'birthdays': data})


