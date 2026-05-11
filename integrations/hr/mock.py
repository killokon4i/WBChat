"""
Mock-провайдер для HR-системы.
Используется для разработки и тестирования без реального подключения к 1С.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import random

from .base import HRProviderInterface


class MockHRProvider(HRProviderInterface):
    """
    Mock HR provider с реалистичными тестовыми данными.
    Имитирует работу с 1С HR-системой.
    """

    # Тестовые данные
    DEPARTMENTS = [
        {'code': 'BANK', 'name': 'WB Банк', 'parent_code': None, 'head_id': 'EMP001'},
        {'code': 'IT', 'name': 'IT-департамент', 'parent_code': 'BANK', 'head_id': 'EMP002'},
        {'code': 'IT-DEV', 'name': 'Отдел разработки', 'parent_code': 'IT', 'head_id': 'EMP003'},
        {'code': 'IT-OPS', 'name': 'Отдел эксплуатации', 'parent_code': 'IT', 'head_id': 'EMP010'},
        {'code': 'IT-SEC', 'name': 'Отдел информационной безопасности', 'parent_code': 'IT', 'head_id': 'EMP015'},
        {'code': 'HR', 'name': 'HR-департамент', 'parent_code': 'BANK', 'head_id': 'EMP020'},
        {'code': 'FIN', 'name': 'Финансовый департамент', 'parent_code': 'BANK', 'head_id': 'EMP030'},
        {'code': 'FIN-ACC', 'name': 'Бухгалтерия', 'parent_code': 'FIN', 'head_id': 'EMP031'},
        {'code': 'RISK', 'name': 'Управление рисками', 'parent_code': 'BANK', 'head_id': 'EMP040'},
        {'code': 'LEGAL', 'name': 'Юридический департамент', 'parent_code': 'BANK', 'head_id': 'EMP050'},
    ]

    POSITIONS = [
        {'code': 'CEO', 'name': 'Генеральный директор', 'is_manager': True},
        {'code': 'CTO', 'name': 'Технический директор', 'is_manager': True},
        {'code': 'HEAD-DEV', 'name': 'Руководитель разработки', 'is_manager': True},
        {'code': 'LEAD-DEV', 'name': 'Ведущий разработчик', 'is_manager': False},
        {'code': 'SENIOR-DEV', 'name': 'Старший разработчик', 'is_manager': False},
        {'code': 'MIDDLE-DEV', 'name': 'Разработчик', 'is_manager': False},
        {'code': 'JUNIOR-DEV', 'name': 'Младший разработчик', 'is_manager': False},
        {'code': 'HEAD-HR', 'name': 'Директор по персоналу', 'is_manager': True},
        {'code': 'HR-BP', 'name': 'HR бизнес-партнёр', 'is_manager': False},
        {'code': 'HR-SPEC', 'name': 'HR-специалист', 'is_manager': False},
        {'code': 'CFO', 'name': 'Финансовый директор', 'is_manager': True},
        {'code': 'ACCOUNTANT', 'name': 'Бухгалтер', 'is_manager': False},
        {'code': 'HEAD-RISK', 'name': 'Руководитель управления рисками', 'is_manager': True},
        {'code': 'RISK-ANALYST', 'name': 'Риск-аналитик', 'is_manager': False},
        {'code': 'HEAD-LEGAL', 'name': 'Начальник юридического отдела', 'is_manager': True},
        {'code': 'LAWYER', 'name': 'Юрист', 'is_manager': False},
    ]

    FIRST_NAMES = ['Александр', 'Дмитрий', 'Максим', 'Сергей', 'Андрей', 'Алексей', 'Артём', 'Илья', 'Кирилл', 'Михаил',
                   'Анна', 'Мария', 'Елена', 'Ольга', 'Наталья', 'Екатерина', 'Татьяна', 'Ирина', 'Светлана', 'Юлия']
    LAST_NAMES = ['Иванов', 'Петров', 'Сидоров', 'Козлов', 'Новиков', 'Морозов', 'Волков', 'Соколов', 'Лебедев', 'Орлов',
                  'Иванова', 'Петрова', 'Сидорова', 'Козлова', 'Новикова', 'Морозова', 'Волкова', 'Соколова', 'Лебедева', 'Орлова']
    MIDDLE_NAMES = ['Александрович', 'Дмитриевич', 'Сергеевич', 'Андреевич', 'Михайлович',
                    'Александровна', 'Дмитриевна', 'Сергеевна', 'Андреевна', 'Михайловна']
    BANDS = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'M1', 'M2', 'M3']

    def __init__(self):
        self._employees = self._generate_employees()

    def _generate_employees(self) -> Dict[str, Dict[str, Any]]:
        """Генерация тестовых сотрудников"""
        employees = {}
        
        # Генерируем 50 сотрудников
        for i in range(1, 51):
            emp_id = f'EMP{i:03d}'
            is_female = random.random() > 0.5
            
            first_name = random.choice(self.FIRST_NAMES[10:] if is_female else self.FIRST_NAMES[:10])
            last_name = random.choice(self.LAST_NAMES[10:] if is_female else self.LAST_NAMES[:10])
            middle_name = random.choice(self.MIDDLE_NAMES[5:] if is_female else self.MIDDLE_NAMES[:5])
            
            dept = random.choice(self.DEPARTMENTS)
            position = random.choice(self.POSITIONS)
            
            hire_date = date.today() - timedelta(days=random.randint(30, 2000))
            birth_date = date.today() - timedelta(days=random.randint(25*365, 55*365))
            
            employees[emp_id] = {
                'employee_id': emp_id,
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'birth_date': birth_date.isoformat(),
                'position_code': position['code'],
                'position_name': position['name'],
                'department_code': dept['code'],
                'department_name': dept['name'],
                'hire_date': hire_date.isoformat(),
                'band': random.choice(self.BANDS),
                'work_phone': f'+7 (495) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}',
                'work_email': f'{first_name.lower()}.{last_name.lower()}@wbbank.ru',
                'manager_id': f'EMP{random.randint(1, 10):03d}' if i > 10 else None,
                'status': 'active',
                'status_end_date': None,
                'updated_at': datetime.now().isoformat(),
            }
        
        return employees

    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Получить данные сотрудника по ID"""
        return self._employees.get(employee_id)

    def get_all_employees(self, updated_since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Получить список всех сотрудников"""
        employees = list(self._employees.values())
        
        if updated_since:
            employees = [
                e for e in employees 
                if datetime.fromisoformat(e['updated_at']) > updated_since
            ]
        
        return employees

    def get_departments(self) -> List[Dict[str, Any]]:
        """Получить список всех подразделений"""
        return [
            {
                'code': d['code'],
                'name': d['name'],
                'parent_code': d['parent_code'],
                'head_employee_id': d['head_id'],
                'is_active': True,
            }
            for d in self.DEPARTMENTS
        ]

    def get_positions(self) -> List[Dict[str, Any]]:
        """Получить список всех должностей"""
        return [
            {
                'code': p['code'],
                'name': p['name'],
                'is_manager': p['is_manager'],
                'is_active': True,
            }
            for p in self.POSITIONS
        ]

    def get_employee_status(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Получить текущий статус сотрудника"""
        employee = self._employees.get(employee_id)
        if not employee:
            return None
        
        # Рандомно генерируем статусы для демонстрации
        if random.random() < 0.1:  # 10% на отпуске
            return {
                'employee_id': employee_id,
                'status': 'vacation',
                'start_date': (date.today() - timedelta(days=3)).isoformat(),
                'end_date': (date.today() + timedelta(days=11)).isoformat(),
                'substitute_id': f'EMP{random.randint(1, 50):03d}',
            }
        
        return {
            'employee_id': employee_id,
            'status': 'active',
            'start_date': None,
            'end_date': None,
            'substitute_id': None,
        }

    def sync_employee(self, employee_id: str) -> bool:
        """Синхронизировать данные конкретного сотрудника"""
        # В mock просто возвращаем True
        return employee_id in self._employees

    def check_connection(self) -> bool:
        """Проверить соединение с HR-системой"""
        # Mock всегда доступен
        return True


