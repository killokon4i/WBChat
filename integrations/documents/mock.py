"""
Mock-провайдер для СЭД Тезис.
Используется для разработки и тестирования.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import random

from .base import DocumentSystemInterface


class MockTezisProvider(DocumentSystemInterface):
    """
    Mock провайдер для СЭД Тезис.
    Имитирует работу с системой электронного документооборота.
    """

    MOCK_DOCUMENTS = [
        {
            'id': 'TEZIS-001',
            'number': 'ПР-001/2026',
            'title': 'О введении в действие Политики информационной безопасности',
            'type': 'order',
            'status': 'approved',
            'created_at': '2026-01-10T10:00:00',
            'author': 'Иванов И.И.',
        },
        {
            'id': 'TEZIS-002',
            'number': 'РГ-015/2026',
            'title': 'Регламент работы с персональными данными',
            'type': 'regulation',
            'status': 'approved',
            'created_at': '2026-01-15T14:30:00',
            'author': 'Петрова М.С.',
        },
        {
            'id': 'TEZIS-003',
            'number': 'ИН-007/2026',
            'title': 'Инструкция по работе с системой документооборота',
            'type': 'instruction',
            'status': 'draft',
            'created_at': '2026-01-20T09:15:00',
            'author': 'Сидоров А.В.',
        },
    ]

    APPROVAL_STAGES = [
        {'stage': 1, 'role': 'Автор', 'status': 'approved', 'date': '2026-01-10T10:00:00'},
        {'stage': 2, 'role': 'Руководитель отдела', 'status': 'approved', 'date': '2026-01-10T14:00:00'},
        {'stage': 3, 'role': 'Юридический отдел', 'status': 'approved', 'date': '2026-01-11T10:00:00'},
        {'stage': 4, 'role': 'Директор', 'status': 'approved', 'date': '2026-01-12T11:00:00'},
    ]

    def __init__(self, base_url: str = 'https://tezis.wbbank.ru'):
        self.base_url = base_url

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Получить документ по ID"""
        for doc in self.MOCK_DOCUMENTS:
            if doc['id'] == document_id:
                return {
                    **doc,
                    'link': self.get_document_link(document_id),
                    'approval_history': self.get_approval_history(document_id),
                }
        return None

    def search_documents(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Поиск документов"""
        results = []
        query_lower = query.lower()
        
        for doc in self.MOCK_DOCUMENTS:
            if query_lower in doc['title'].lower() or query_lower in doc['number'].lower():
                results.append({
                    **doc,
                    'link': self.get_document_link(doc['id']),
                })
        
        # Применяем фильтры
        if filters:
            if 'type' in filters:
                results = [d for d in results if d['type'] == filters['type']]
            if 'status' in filters:
                results = [d for d in results if d['status'] == filters['status']]
        
        return results

    def get_approval_history(self, document_id: str) -> List[Dict[str, Any]]:
        """Получить историю согласования"""
        # Для mock возвращаем стандартную историю
        return [
            {
                **stage,
                'document_id': document_id,
                'approver': f'Сотрудник {stage["stage"]}',
                'comment': 'Согласовано' if stage['status'] == 'approved' else '',
            }
            for stage in self.APPROVAL_STAGES
        ]

    def get_document_link(self, document_id: str) -> str:
        """Получить ссылку на документ"""
        return f'{self.base_url}/documents/{document_id}'

    def check_connection(self) -> bool:
        """Проверить соединение"""
        return True


