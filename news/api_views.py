from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from .models import News
from .serializers import NewsListSerializer, NewsDetailSerializer, NewsCreateSerializer


class IsModeratorOrReadOnly(permissions.BasePermission):
    """
    Разрешение: модераторы могут всё, остальные только читать
    """
    def has_permission(self, request, view):
        # Разрешаем GET, HEAD, OPTIONS всем аутентифицированным
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Для остальных методов нужны права модератора
        return request.user.is_authenticated and request.user.isModerator


class NewsViewSet(viewsets.ModelViewSet):
    """
    API для работы с новостями
    """
    permission_classes = [IsModeratorOrReadOnly]
    queryset = News.objects.all().order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return NewsListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return NewsCreateSerializer
        return NewsDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Проверяем права
        if not request.user.isModerator:
            return Response(
                {'error': 'Недостаточно прав для удаления'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


