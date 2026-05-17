from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count

from .models import (
    NotificationChannel, NotificationType,
    Notification, UserNotificationSettings
)
from .serializers import (
    NotificationChannelSerializer, NotificationTypeSerializer,
    NotificationSerializer, UserNotificationSettingsSerializer,
    NotificationCountSerializer
)


class NotificationChannelViewSet(viewsets.ReadOnlyModelViewSet):
    """API для каналов уведомлений"""
    queryset = NotificationChannel.objects.filter(is_active=True)
    serializer_class = NotificationChannelSerializer
    permission_classes = [IsAuthenticated]


class NotificationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API для типов уведомлений"""
    queryset = NotificationType.objects.filter(is_active=True)
    serializer_class = NotificationTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Фильтр по категории
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        
        return qs.order_by('category', 'name')


class NotificationViewSet(viewsets.ModelViewSet):
    """
    API для уведомлений пользователя.
    
    list: Получить уведомления
    retrieve: Получить уведомление
    mark_read: Отметить как прочитанное
    mark_all_read: Отметить все как прочитанные
    count: Получить счётчики
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(user=self.request.user)
        
        # Фильтр по прочитанности
        unread_only = self.request.query_params.get('unread', 'false').lower() == 'true'
        if unread_only:
            qs = qs.filter(is_read=False)
        
        # Фильтр по типу
        notification_type = self.request.query_params.get('type')
        if notification_type:
            qs = qs.filter(notification_type__code=notification_type)
        
        # Фильтр по приоритету
        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)
        
        return qs.select_related('notification_type').order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Отметить уведомление как прочитанное"""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Отметить все уведомления как прочитанные"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({'marked_read': count})

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Получить счётчики уведомлений"""
        qs = Notification.objects.filter(user=request.user)
        
        total = qs.count()
        unread = qs.filter(is_read=False).count()
        
        # Группировка по типам
        by_type = dict(
            qs.filter(is_read=False)
            .values('notification_type__code')
            .annotate(count=Count('id'))
            .values_list('notification_type__code', 'count')
        )
        
        return Response({
            'total': total,
            'unread': unread,
            'by_type': by_type,
        })


class UserNotificationSettingsViewSet(viewsets.ModelViewSet):
    """API для настроек уведомлений пользователя"""
    queryset = UserNotificationSettings.objects.all()
    serializer_class = UserNotificationSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(
            user=self.request.user
        ).select_related('notification_type')

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Получить текущие настройки пользователя"""
        settings = self.get_queryset()
        serializer = self.get_serializer(settings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Массовое обновление настроек"""
        settings_data = request.data.get('settings', [])
        updated = []
        
        for item in settings_data:
            notification_type_id = item.get('notification_type')
            if not notification_type_id:
                continue
            
            setting, created = UserNotificationSettings.objects.update_or_create(
                user=request.user,
                notification_type_id=notification_type_id,
                defaults={
                    'in_app_enabled': item.get('in_app_enabled', True),
                    'email_enabled': item.get('email_enabled', True),
                    'push_enabled': item.get('push_enabled', True),
                    'email_frequency': item.get('email_frequency', 'instant'),
                }
            )
            updated.append(setting)
        
        serializer = self.get_serializer(updated, many=True)
        return Response(serializer.data)


