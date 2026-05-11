"""
Базовые интерфейсы для интеграций.
Определяют контракты для всех провайдеров.
"""
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime


class IntegrationError(Exception):
    """Базовое исключение для ошибок интеграции"""
    pass


class ConnectionError(IntegrationError):
    """Ошибка подключения к внешней системе"""
    pass


class AuthenticationError(IntegrationError):
    """Ошибка аутентификации во внешней системе"""
    pass


class DataValidationError(IntegrationError):
    """Ошибка валидации данных"""
    pass


