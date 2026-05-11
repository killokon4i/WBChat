from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ConversationViewSet, MessageViewSet, UserViewSet

# Основной роутер
router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    # Вложенные маршруты для сообщений
    path(
        'conversations/<int:conversation_pk>/messages/',
        MessageViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='conversation-messages-list'
    ),
    path(
        'conversations/<int:conversation_pk>/messages/<int:pk>/',
        MessageViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
        name='conversation-messages-detail'
    ),
    path(
        'conversations/<int:conversation_pk>/messages/<int:pk>/react/',
        MessageViewSet.as_view({'post': 'react'}),
        name='conversation-messages-react'
    ),
    path(
        'conversations/<int:conversation_pk>/messages/<int:pk>/edit/',
        MessageViewSet.as_view({'post': 'edit'}),
        name='conversation-messages-edit'
    ),
]
