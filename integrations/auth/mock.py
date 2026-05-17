"""
Mock-провайдер для аутентификации.
Используется для разработки и тестирования без Keycloak.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import hashlib


class MockAuthProvider:
    """
    Mock провайдер аутентификации.
    Имитирует работу Keycloak для разработки.
    """

    def __init__(self):
        self._tokens = {}  # token -> user_data
        self._refresh_tokens = {}  # refresh_token -> token

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Аутентифицировать пользователя.
        В mock принимает любые credentials.
        """
        # Генерируем токены
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        
        user_data = {
            'sub': hashlib.md5(username.encode()).hexdigest(),
            'preferred_username': username,
            'email': f'{username}@wbbank.ru',
            'name': username.title(),
            'roles': ['user'],
        }
        
        self._tokens[access_token] = {
            'user': user_data,
            'expires_at': datetime.now() + timedelta(hours=1),
        }
        self._refresh_tokens[refresh_token] = access_token
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'user': user_data,
        }

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Валидировать токен"""
        token_data = self._tokens.get(token)
        if not token_data:
            return None
        
        if datetime.now() > token_data['expires_at']:
            del self._tokens[token]
            return None
        
        return token_data['user']

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Обновить токен"""
        old_token = self._refresh_tokens.get(refresh_token)
        if not old_token:
            return None
        
        token_data = self._tokens.get(old_token)
        if not token_data:
            return None
        
        # Генерируем новые токены
        new_access_token = secrets.token_urlsafe(32)
        new_refresh_token = secrets.token_urlsafe(32)
        
        # Удаляем старые
        del self._tokens[old_token]
        del self._refresh_tokens[refresh_token]
        
        # Сохраняем новые
        self._tokens[new_access_token] = {
            'user': token_data['user'],
            'expires_at': datetime.now() + timedelta(hours=1),
        }
        self._refresh_tokens[new_refresh_token] = new_access_token
        
        return {
            'access_token': new_access_token,
            'refresh_token': new_refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
        }

    def logout(self, token: str) -> bool:
        """Выход из системы"""
        if token in self._tokens:
            del self._tokens[token]
            # Удаляем связанный refresh token
            for rt, at in list(self._refresh_tokens.items()):
                if at == token:
                    del self._refresh_tokens[rt]
                    break
            return True
        return False

    def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о пользователе"""
        return self.validate_token(token)

    def check_connection(self) -> bool:
        """Проверить соединение"""
        return True


