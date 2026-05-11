"""
Провайдер для интеграции с Keycloak.
Заготовка для будущей реализации.
"""
from typing import Optional, Dict, Any

from .base import AuthProviderInterface
from ..base import ConnectionError, AuthenticationError


class KeycloakProvider(AuthProviderInterface):
    """
    Провайдер для работы с Keycloak IdP.
    
    TODO: Реализовать после настройки Keycloak.
    
    Требуемые настройки в settings.py:
    - INTEGRATIONS['KEYCLOAK_URL']: URL Keycloak
    - INTEGRATIONS['KEYCLOAK_REALM']: Realm (WB Bank)
    - INTEGRATIONS['KEYCLOAK_CLIENT_ID']: Client ID
    - INTEGRATIONS['KEYCLOAK_CLIENT_SECRET']: Client Secret
    """

    def __init__(self, server_url: str, realm: str, client_id: str, client_secret: str):
        self.server_url = server_url
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Аутентифицировать пользователя"""
        # TODO: POST /realms/{realm}/protocol/openid-connect/token
        raise NotImplementedError("Keycloak integration not implemented yet")

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Валидировать токен"""
        # TODO: POST /realms/{realm}/protocol/openid-connect/token/introspect
        raise NotImplementedError("Keycloak integration not implemented yet")

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Обновить токен"""
        # TODO: POST /realms/{realm}/protocol/openid-connect/token
        raise NotImplementedError("Keycloak integration not implemented yet")

    def logout(self, token: str) -> bool:
        """Выход из системы"""
        # TODO: POST /realms/{realm}/protocol/openid-connect/logout
        raise NotImplementedError("Keycloak integration not implemented yet")

    def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о пользователе"""
        # TODO: GET /realms/{realm}/protocol/openid-connect/userinfo
        raise NotImplementedError("Keycloak integration not implemented yet")

    def check_connection(self) -> bool:
        """Проверить соединение"""
        # TODO: GET /realms/{realm}/.well-known/openid-configuration
        raise NotImplementedError("Keycloak integration not implemented yet")


