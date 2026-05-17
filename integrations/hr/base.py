"""
Базовый интерфейс для HR-провайдеров.
Определяет методы для работы с данными сотрудников из HR-системы.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class HRProviderInterface(ABC):
    """
    Абстрактный интерфейс для HR-провайдеров.
    Реализации: MockHRProvider, OneCHRProvider
    """

    @abstractmethod
    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить данные сотрудника по ID.
        
        Args:
            employee_id: Уникальный идентификатор сотрудника в HR-системе
            
        Returns:
            Словарь с данными сотрудника или None если не найден
        """
        pass

    @abstractmethod
    def get_all_employees(self, updated_since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Получить список всех сотрудников.
        
        Args:
            updated_since: Если указано, вернуть только изменённых после этой даты
            
        Returns:
            Список словарей с данными сотрудников
        """
        pass

    @abstractmethod
    def get_departments(self) -> List[Dict[str, Any]]:
        """
        Получить список всех подразделений.
        
        Returns:
            Список словарей с данными подразделений
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Получить список всех должностей.
        
        Returns:
            Список словарей с данными должностей
        """
        pass

    @abstractmethod
    def get_employee_status(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить текущий статус сотрудника (отпуск, больничный и т.д.).
        
        Args:
            employee_id: ID сотрудника
            
        Returns:
            Словарь со статусом или None
        """
        pass

    @abstractmethod
    def sync_employee(self, employee_id: str) -> bool:
        """
        Синхронизировать данные конкретного сотрудника.
        
        Args:
            employee_id: ID сотрудника
            
        Returns:
            True если синхронизация успешна
        """
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        """
        Проверить соединение с HR-системой.
        
        Returns:
            True если соединение активно
        """
        pass


