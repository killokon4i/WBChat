from rest_framework import serializers
from .models import (
    NotificationChannel, NotificationType,
    Notification, UserNotificationSettings
)


class NotificationChannelSerializer(serializers.ModelSerializer):
    """Сериализатор канала уведомлений"""
    class Meta:
        model = NotificationChannel
        fields = ['id', 'code', 'name', 'description', 'icon', 'is_active', 'order']


class NotificationTypeSerializer(serializers.ModelSerializer):
    """Сериализатор типа уведомления"""
    default_channels = NotificationChannelSerializer(many=True, read_only=True)

    class Meta:
        model = NotificationType
        fields = [
            'id', 'code', 'name', 'description', 'category',
            'icon', 'color', 'priority',
            'default_channels', 'is_active', 'can_be_disabled'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """Сериализатор уведомления"""
    type_name = serializers.CharField(source='notification_type.name', read_only=True)
    type_icon = serializers.CharField(source='notification_type.icon', read_only=True)
    type_color = serializers.CharField(source='notification_type.color', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'type_name', 'type_icon', 'type_color',
            'title', 'content', 'link',
            'priority', 'is_read', 'read_at',
            'created_at', 'expires_at',
            'grouped_count'
        ]
        read_only_fields = ['created_at', 'read_at']


class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    """Сериализатор настроек уведомлений пользователя"""
    notification_type_name = serializers.CharField(source='notification_type.name', read_only=True)

    class Meta:
        model = UserNotificationSettings
        fields = [
            'id', 'notification_type', 'notification_type_name',
            'in_app_enabled', 'email_enabled', 'push_enabled',
            'email_frequency', 'digest_time', 'digest_day'
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NotificationCountSerializer(serializers.Serializer):
    """Сериализатор счётчика уведомлений"""
    total = serializers.IntegerField()
    unread = serializers.IntegerField()
    by_type = serializers.DictField(child=serializers.IntegerField())


