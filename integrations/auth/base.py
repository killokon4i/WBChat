"""
Базовый интерфейс для провайдеров аутентификации.
Определяет методы для SSO и управления сессиями.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AuthProviderInterface(ABC):
    """
    Абстрактный интерфейс для провайдеров аутентификации.
    Реализации: MockAuthProvider, KeycloakProvider
    """

    @abstractmethod
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Аутентифицировать пользователя.
        
        Args:
            username: Логин
            password: Пароль
            
        Returns:
            Словарь с данными пользователя и токенами или None
        """
        pass

    @abstractmethod
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Валидировать токен.
        
        Args:
            token: Access token
            
        Returns:
            Данные токена или None если невалиден
        """
        pass

    @abstractmethod
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Обновить токен.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Новые токены или None
        """
        pass

    @abstractmethod
    def logout(self, token: str) -> bool:
        """
        Выход из системы (инвалидация токена).
        
        Args:
            token: Access token
            
        Returns:
            True если успешно
        """
        pass

    @abstractmethod
    def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о пользователе по токену.
        
        Args:
            token: Access token
            
        Returns:
            Данные пользователя или None
        """
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        """
        Проверить соединение с IdP.
        
        Returns:
            True если соединение активно
        """
        pass


