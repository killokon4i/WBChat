from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_index, name='chat_index'),
    path('start/<int:user_id>/', views.start_chat, name='start_chat'),
    path('<int:conversation_id>/', views.chat_room, name='chat_room'),
    path('api/messages/<int:conversation_id>/', views.get_messages, name='chat_messages'),
    path('api/create/', views.create_conversation, name='create_conversation'),
    path('api/upload/<int:conversation_id>/', views.upload_attachment, name='chat_upload'),
    path('api/pin/<int:conversation_id>/<int:message_id>/', views.pin_message, name='chat_pin'),
    path('api/conversations/', views.api_conversations_list, name='chat_api_conversations'),
    path('api/inbox-sync/', views.api_inbox_sync, name='chat_api_inbox_sync'),
    path('api/attachment/<int:attachment_id>/download/', views.download_attachment, name='chat_download_attachment'),
    path('api/forward/<int:conversation_id>/<int:message_id>/', views.forward_message, name='chat_forward'),
    path('api/mark-read/<int:conversation_id>/', views.mark_read, name='chat_mark_read'),
    path('api/presence/<int:conversation_id>/', views.api_presence, name='chat_presence'),
    path('api/create-group/', views.create_group, name='chat_create_group'),
    path('api/info/<int:conversation_id>/', views.chat_info, name='chat_info'),
    path('api/update/<int:conversation_id>/', views.chat_update, name='chat_update'),
    path('api/add-member/<int:conversation_id>/', views.chat_add_member, name='chat_add_member'),
    path('api/remove-member/<int:conversation_id>/', views.chat_remove_member, name='chat_remove_member'),
]
