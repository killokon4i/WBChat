from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'channels', api_views.NotificationChannelViewSet, basename='notification-channel')
router.register(r'types', api_views.NotificationTypeViewSet, basename='notification-type')
router.register(r'notifications', api_views.NotificationViewSet, basename='notification')
router.register(r'settings', api_views.UserNotificationSettingsViewSet, basename='notification-settings')

urlpatterns = [
    path('', include(router.urls)),
]


