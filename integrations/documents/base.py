"""
Базовый интерфейс для интеграции с СЭД.
Определяет методы для работы с внешними системами документооборота.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class DocumentSystemInterface(ABC):
    """
    Абстрактный интерфейс для провайдеров СЭД.
    Реализации: MockTezisProvider, TezisProvider
    """

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить документ по ID.
        
        Args:
            document_id: ID документа в СЭД
            
        Returns:
            Метаданные документа или None
        """
        pass

    @abstractmethod
    def search_documents(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Поиск документов.
        
        Args:
            query: Поисковый запрос
            filters: Дополнительные фильтры
            
        Returns:
            Список документов
        """
        pass

    @abstractmethod
    def get_approval_history(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Получить историю согласования документа.
        
        Args:
            document_id: ID документа
            
        Returns:
            Список этапов согласования
        """
        pass

    @abstractmethod
    def get_document_link(self, document_id: str) -> str:
        """
        Получить ссылку на документ в СЭД.
        
        Args:
            document_id: ID документа
            
        Returns:
            URL документа
        """
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        """
        Проверить соединение с СЭД.
        
        Returns:
            True если соединение активно
        """
        pass


