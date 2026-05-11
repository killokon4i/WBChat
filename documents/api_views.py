from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import (
    DocumentCategory, Document, DocumentVersion,
    DocumentAcknowledgement
)
from .serializers import (
    DocumentCategorySerializer,
    DocumentListSerializer, DocumentDetailSerializer,
    DocumentVersionSerializer,
    DocumentAcknowledgementSerializer
)
from .services import DocumentSearchService, DocumentAccessService


search_service = DocumentSearchService()
access_service = DocumentAccessService()


class DocumentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для категорий документов"""
    queryset = DocumentCategory.objects.filter(is_active=True)
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Только корневые категории
        root_only = self.request.query_params.get('root_only', 'false').lower() == 'true'
        if root_only:
            qs = qs.filter(parent__isnull=True)
        
        return qs.order_by('order', 'name')


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для работы с документами.
    
    list: Поиск и фильтрация документов
    retrieve: Получить документ по ID
    versions: Получить версии документа
    download: Скачать файл
    search: Полнотекстовый поиск
    """
    queryset = Document.objects.filter(status='active')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DocumentDetailSerializer
        return DocumentListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Фильтры
        doc_type = self.request.query_params.get('type')
        if doc_type:
            qs = qs.filter(document_type=doc_type)
        
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)
        
        confidentiality = self.request.query_params.get('confidentiality')
        if confidentiality:
            qs = qs.filter(confidentiality=confidentiality)
        
        # Безопасная фильтрация
        # TODO: Применить access service для фильтрации
        
        return qs.select_related('category', 'author').order_by('-updated_at')

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Полнотекстовый поиск документов"""
        query = request.query_params.get('q', '')
        page = int(request.query_params.get('page', 1))
        
        filters = {}
        if request.query_params.get('type'):
            filters['document_type'] = request.query_params['type']
        if request.query_params.get('category'):
            filters['category'] = request.query_params['category']
        
        result = search_service.search(
            query=query,
            user=request.user,
            filters=filters,
            page=page
        )
        
        serializer = DocumentListSerializer(result['results'], many=True)
        
        return Response({
            'results': serializer.data,
            'total': result['total'],
            'page': result['page'],
            'pages': result['pages'],
            'facets': result['facets'],
        })

    @action(detail=False, methods=['get'])
    def suggest(self, request):
        """Автодополнение для поиска"""
        query = request.query_params.get('q', '')
        suggestions = search_service.suggest(query, request.user)
        return Response(suggestions)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Получить версии документа"""
        document = self.get_object()
        versions = document.versions.select_related('uploaded_by').order_by('-version_number')
        serializer = DocumentVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Получить права текущего пользователя на документ"""
        document = self.get_object()
        permissions = access_service.get_user_permissions(document, request.user)
        return Response(permissions)


class DocumentAcknowledgementViewSet(viewsets.ModelViewSet):
    """
    API для ознакомления с документами.
    
    list: Список документов к ознакомлению
    acknowledge: Отметить как прочитанный
    """
    queryset = DocumentAcknowledgement.objects.all()
    serializer_class = DocumentAcknowledgementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # По умолчанию только для текущего пользователя
        qs = qs.filter(user=self.request.user)
        
        # Фильтр по статусу
        pending_only = self.request.query_params.get('pending', 'false').lower() == 'true'
        if pending_only:
            qs = qs.filter(acknowledged_at__isnull=True)
        
        required_only = self.request.query_params.get('required', 'false').lower() == 'true'
        if required_only:
            qs = qs.filter(required=True)
        
        return qs.select_related('document', 'user').order_by('-document__updated_at')

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Отметить документ как прочитанный"""
        acknowledgement = self.get_object()
        
        if acknowledgement.user != request.user:
            return Response(
                {'error': 'Вы не можете отметить прочтение за другого пользователя'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if acknowledgement.acknowledged_at:
            return Response(
                {'error': 'Документ уже отмечен как прочитанный'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        acknowledgement.acknowledged_at = timezone.now()
        acknowledgement.acknowledged_version = acknowledgement.document.get_current_version()
        acknowledgement.save()
        
        serializer = self.get_serializer(acknowledgement)
        return Response(serializer.data)


