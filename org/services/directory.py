from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from ..models import Department, Position

User = get_user_model()


class DirectoryService:
    """Сервис для работы со справочником сотрудников"""

    def search_employees(self, query: str, department_id: int = None, limit: int = 50):
        """
        Поиск сотрудников по имени, фамилии, должности, email.
        """
        qs = User.objects.filter(is_active=True, is_archived=False)

        if query:
            qs = qs.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(work_email__icontains=query) |
                Q(position__name__icontains=query)
            )

        if department_id:
            # Включаем всех сотрудников подразделения и его дочерних
            department = Department.objects.filter(id=department_id).first()
            if department:
                dept_ids = [department.id]
                dept_ids.extend(
                    department.get_descendants().values_list('id', flat=True)
                )
                qs = qs.filter(department_id__in=dept_ids)

        return qs.select_related('department', 'position').order_by('last_name', 'first_name')[:limit]

    def get_department_tree(self, root_id: int = None):
        """
        Получить дерево подразделений с количеством сотрудников.
        """
        qs = Department.objects.filter(is_active=True)

        if root_id:
            root = Department.objects.filter(id=root_id).first()
            if root:
                qs = qs.filter(Q(id=root_id) | Q(path__startswith=f"{root.path}/"))
        else:
            qs = qs.filter(parent__isnull=True)

        # Добавляем количество сотрудников
        qs = qs.annotate(
            employee_count=Count(
                'employees',
                filter=Q(employees__is_active=True, employees__is_archived=False)
            )
        )

        return qs.order_by('path', 'name')

    def get_employee_card(self, user_id: int):
        """
        Получить полную карточку сотрудника для справочника.
        """
        try:
            user = User.objects.select_related(
                'department', 'position', 'manager', 'hr_partner', 'substitute'
            ).get(id=user_id)

            return {
                'id': user.id,
                'full_name': user.get_full_name() or user.username,
                'username': user.username,
                'avatar': user.avatar.url if user.avatar else None,
                'position': user.position.name if user.position else None,
                'department': {
                    'id': user.department.id,
                    'name': user.department.name,
                } if user.department else None,
                'work_phone': user.work_phone,
                'work_email': user.work_email,
                'personal_phone': user.personal_phone if self._can_see_personal(user) else None,
                'telegram': user.telegram,
                'birth_date': user.birth_date,
                'hire_date': user.hire_date,
                'band': user.band,
                'status': user.status,
                'status_end_date': user.status_end_date,
                'substitute': {
                    'id': user.substitute.id,
                    'name': user.substitute.get_full_name(),
                } if user.substitute else None,
                'manager': {
                    'id': user.manager.id,
                    'name': user.manager.get_full_name(),
                } if user.manager else None,
                'about': user.about,
            }
        except User.DoesNotExist:
            return None

    def _can_see_personal(self, user) -> bool:
        """Проверка видимости личных данных (упрощённая)"""
        # В будущем здесь будет проверка настроек приватности
        return bool(user.personal_phone)

    def get_department_employees(self, department_id: int, include_children: bool = False):
        """
        Получить список сотрудников подразделения.
        """
        department = Department.objects.filter(id=department_id).first()
        if not department:
            return User.objects.none()

        if include_children:
            dept_ids = [department.id]
            dept_ids.extend(
                department.get_descendants().values_list('id', flat=True)
            )
            return User.objects.filter(
                department_id__in=dept_ids,
                is_active=True,
                is_archived=False
            ).select_related('position').order_by('last_name', 'first_name')
        
        return department.get_employees().select_related('position').order_by('last_name', 'first_name')

    def get_subordinates(self, manager_id: int, direct_only: bool = True):
        """
        Получить подчинённых сотрудника.
        """
        if direct_only:
            return User.objects.filter(
                manager_id=manager_id,
                is_active=True,
                is_archived=False
            ).select_related('department', 'position')
        
        # Рекурсивно получить всех подчинённых
        all_subordinates = []
        direct = list(User.objects.filter(
            manager_id=manager_id,
            is_active=True,
            is_archived=False
        ))
        all_subordinates.extend(direct)
        
        for sub in direct:
            all_subordinates.extend(
                self.get_subordinates(sub.id, direct_only=False)
            )
        
        return all_subordinates


