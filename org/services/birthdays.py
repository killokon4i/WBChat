from datetime import date, timedelta
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()


class BirthdayService:
    """Сервис для работы с днями рождения сотрудников"""

    def get_upcoming_birthdays(self, days: int = 14, department_id: int = None):
        """
        Получить список ближайших дней рождения.
        
        Args:
            days: Количество дней вперёд для поиска
            department_id: ID подразделения для фильтрации (опционально)
        
        Returns:
            QuerySet сотрудников с ближайшими днями рождения
        """
        today = date.today()
        
        # Базовый queryset
        qs = User.objects.filter(
            is_active=True,
            is_archived=False,
            birth_date__isnull=False
        )
        
        if department_id:
            from ..models import Department
            department = Department.objects.filter(id=department_id).first()
            if department:
                dept_ids = [department.id]
                dept_ids.extend(
                    department.get_descendants().values_list('id', flat=True)
                )
                qs = qs.filter(department_id__in=dept_ids)
        
        # Собираем дни рождения на ближайшие N дней
        birthdays = []
        for user in qs.select_related('department', 'position'):
            if user.birth_date:
                # Вычисляем дату рождения в этом году
                try:
                    birthday_this_year = user.birth_date.replace(year=today.year)
                except ValueError:
                    # 29 февраля в не високосный год
                    birthday_this_year = user.birth_date.replace(year=today.year, day=28)
                
                # Если день рождения уже прошёл, берём следующий год
                if birthday_this_year < today:
                    try:
                        birthday_this_year = user.birth_date.replace(year=today.year + 1)
                    except ValueError:
                        birthday_this_year = user.birth_date.replace(year=today.year + 1, day=28)
                
                days_until = (birthday_this_year - today).days
                
                if 0 <= days_until <= days:
                    birthdays.append({
                        'user': user,
                        'date': birthday_this_year,
                        'days_until': days_until,
                        'age': self._calculate_age(user.birth_date, birthday_this_year),
                    })
        
        # Сортируем по дате
        birthdays.sort(key=lambda x: x['days_until'])
        
        return birthdays

    def get_today_birthdays(self, department_id: int = None):
        """
        Получить сотрудников, у которых сегодня день рождения.
        """
        today = date.today()
        
        qs = User.objects.filter(
            is_active=True,
            is_archived=False,
            birth_date__month=today.month,
            birth_date__day=today.day
        )
        
        if department_id:
            from ..models import Department
            department = Department.objects.filter(id=department_id).first()
            if department:
                dept_ids = [department.id]
                dept_ids.extend(
                    department.get_descendants().values_list('id', flat=True)
                )
                qs = qs.filter(department_id__in=dept_ids)
        
        result = []
        for user in qs.select_related('department', 'position'):
            result.append({
                'user': user,
                'age': self._calculate_age(user.birth_date),
            })
        
        return result

    def get_birthdays_in_month(self, month: int, year: int = None, department_id: int = None):
        """
        Получить все дни рождения в указанном месяце.
        """
        if year is None:
            year = date.today().year
        
        qs = User.objects.filter(
            is_active=True,
            is_archived=False,
            birth_date__month=month
        )
        
        if department_id:
            from ..models import Department
            department = Department.objects.filter(id=department_id).first()
            if department:
                dept_ids = [department.id]
                dept_ids.extend(
                    department.get_descendants().values_list('id', flat=True)
                )
                qs = qs.filter(department_id__in=dept_ids)
        
        result = []
        for user in qs.select_related('department', 'position').order_by('birth_date__day'):
            try:
                birthday_date = user.birth_date.replace(year=year)
            except ValueError:
                birthday_date = user.birth_date.replace(year=year, day=28)
            
            result.append({
                'user': user,
                'date': birthday_date,
                'age': self._calculate_age(user.birth_date, birthday_date),
            })
        
        return result

    def _calculate_age(self, birth_date: date, as_of_date: date = None) -> int:
        """Вычислить возраст"""
        if as_of_date is None:
            as_of_date = date.today()
        
        age = as_of_date.year - birth_date.year
        
        # Корректировка если день рождения ещё не наступил
        if (as_of_date.month, as_of_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age


