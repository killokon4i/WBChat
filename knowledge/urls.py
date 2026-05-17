from django.urls import path, register_converter
from . import views
from .converters import UnicodeSlugConverter

register_converter(UnicodeSlugConverter, 'uslug')

urlpatterns = [
    path('', views.knowledge_home, name='kb_home'),
    path('search/', views.search, name='kb_search'),
    path('search/suggest/', views.search_suggest, name='kb_search_suggest'),
    path('tags/autocomplete/', views.tags_autocomplete, name='kb_tags_autocomplete'),
    path('mentions/autocomplete/', views.mention_autocomplete, name='kb_mention_autocomplete'),

    path('faq/', views.faq_list, name='kb_faq'),
    path('faq/<int:faq_id>/helpful/', views.faq_helpful, name='kb_faq_helpful'),
    path('faq/<int:faq_id>/escalate/', views.faq_escalate, name='kb_faq_escalate'),

    path('tag/<uslug:slug>/', views.tag_view, name='kb_tag'),
    path('tag/<uslug:slug>/delete/', views.tag_delete, name='kb_tag_delete'),
    path('category/<uslug:slug>/', views.category_view, name='kb_category'),
    path('categories/reorder/', views.reorder_categories, name='kb_reorder_categories'),

    path('article/create/', views.article_create, name='kb_article_create'),
    path('article/preview/', views.article_preview, name='kb_article_preview'),
    path('article/<uslug:slug>/', views.article_detail, name='kb_article_detail'),
    path('article/<uslug:slug>/edit/', views.article_edit, name='kb_article_edit'),
    path('article/<uslug:slug>/delete/', views.article_delete, name='kb_article_delete'),
    path('article/<uslug:slug>/unarchive/', views.article_unarchive, name='kb_article_unarchive'),
    path('article/<uslug:slug>/publish/', views.article_publish, name='kb_article_publish'),
    path('article/<uslug:slug>/versions/', views.article_versions, name='kb_article_versions'),
    path('article/<uslug:slug>/diff/<int:v1>/<int:v2>/', views.article_diff, name='kb_article_diff'),
    path('article/<uslug:slug>/rollback/<int:version_number>/', views.article_rollback, name='kb_article_rollback'),
    path('article/<uslug:slug>/autosave/', views.article_autosave, name='kb_article_autosave'),
    path('article/<uslug:slug>/quality-check/', views.article_quality_check, name='kb_article_quality_check'),

    path('article/<uslug:slug>/comment/', views.add_comment, name='kb_add_comment'),
    path('article/<uslug:slug>/comment/<int:comment_id>/edit/', views.edit_comment, name='kb_edit_comment'),
    path('article/<uslug:slug>/comment/<int:comment_id>/delete/', views.delete_comment, name='kb_delete_comment'),
    path('article/<uslug:slug>/rate/', views.rate_article, name='kb_rate_article'),
    path('article/<uslug:slug>/track-time/', views.track_time, name='kb_track_time'),

    path('article/<uslug:slug>/attachments/upload/', views.upload_attachment, name='kb_upload_attachment'),
    path('article/<uslug:slug>/attachments/<int:attachment_id>/delete/', views.delete_attachment, name='kb_delete_attachment'),

    path('article/<uslug:slug>/suggest-edit/', views.suggest_edit, name='kb_suggest_edit'),
    path('article/<uslug:slug>/suggested-edits/', views.suggested_edits_list, name='kb_suggested_edits'),
    path('article/<uslug:slug>/suggested-edits/<int:edit_id>/review/', views.review_suggested_edit, name='kb_review_suggested_edit'),

    path('subscribe/<str:target_type>/<int:target_id>/', views.toggle_subscription, name='kb_toggle_subscription'),

    path('article/<uslug:slug>/lock/extend/', views.extend_lock, name='kb_extend_lock'),
    path('article/<uslug:slug>/lock/release/', views.release_lock, name='kb_release_lock'),

    path('terms/request/', views.request_term, name='kb_request_term'),
    path('terms/requests/', views.term_requests_list, name='kb_term_requests'),
    path('terms/requests/<int:request_id>/review/', views.review_term_request, name='kb_review_term_request'),

    path('statistics/', views.statistics_view, name='kb_statistics'),
    path('dashboard/', views.personal_dashboard, name='kb_personal_dashboard'),
    path('export/', views.export_articles, name='kb_export_csv'),

    path('api/global-search/', views.global_search_api, name='kb_global_search'),
    path('share/conversations/', views.share_conversations, name='kb_share_conversations'),
    path('article/<uslug:slug>/share/', views.share_article, name='kb_share_article'),
]
