from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.conf import settings
from django.views.static import serve
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.views import register, login_view, profile_view, logout_view, profile_edit, home, dashboard
from news.views import news_detail, news_list, edit_news, delete_news, create_news, add_comment, delete_comment, edit_comment, mention_autocomplete, toggle_reaction, share_conversations as news_share_conversations, share_news, delete_news_attachment, news_autosave, news_preview, news_personal_dashboard

urlpatterns = [
    # Главная
    path('', home, name='home'),
    
    # Админка
    path('admin/', admin.site.urls),
    
    # Аутентификация
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Профиль и Личный кабинет
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('dashboard/', dashboard, name='dashboard'),
    
    # Новости
    path('news/', news_list, name='news_list'),
    path('news/dashboard/', news_personal_dashboard, name='news_personal_dashboard'),
    path('news/<int:pk>/', news_detail, name='news_detail'),
    path('news/<int:pk>/edit/', edit_news, name='news_edit'),
    path('news/<int:pk>/delete/', delete_news, name='news_delete'),
    path('news/<int:pk>/attachments/<int:attachment_id>/delete/', delete_news_attachment, name='delete_news_attachment'),
    path('news/<int:pk>/autosave/', news_autosave, name='news_autosave'),
    path('news/preview/', news_preview, name='news_preview'),
    path('news/create/', create_news, name='create_news'),
    path('news/<int:pk>/comment/', add_comment, name='add_comment'),
    path('news/<int:pk>/comment/<int:comment_id>/delete/', delete_comment, name='delete_comment'),
    path('news/<int:pk>/comment/<int:comment_id>/edit/', edit_comment, name='edit_comment'),
    path('news/<int:pk>/reaction/', toggle_reaction, name='toggle_reaction'),
    path('news/share/conversations/', news_share_conversations, name='news_share_conversations'),
    path('news/<int:pk>/share/', share_news, name='news_share'),

    # Опросы
    path('surveys/', include('surveys.urls')),
    
    # API упоминаний
    path('api/mentions/autocomplete/', mention_autocomplete, name='mention_autocomplete'),
    
    # Чат
    path('chat/', include('chat.urls')),
    
    # Справочник сотрудников / Оргструктура
    path('directory/', include('org.urls')),
    
    # Документы
    path('documents/', include('documents.urls')),
    
    # База знаний
    path('knowledge/', include('knowledge.urls')),
    path('tinymce/', include('tinymce.urls')),

    # Уведомления
    path('notifications/', include('notifications.urls')),
    
    # API
    path('api/chat/', include('chat.api_urls')),
    path('api/news/', include('news.api_urls')),
    path('api/org/', include('org.api_urls')),
    path('api/documents/', include('documents.api_urls')),
    path('api/notifications/', include('notifications.api_urls')),
    
    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()

if not getattr(settings, 'USE_S3_MEDIA', False):
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]

handler404 = 'WBChat.error_views.custom_404'
handler403 = 'WBChat.error_views.custom_403'
handler500 = 'WBChat.error_views.custom_500'
