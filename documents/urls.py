from django.urls import path
from . import views

urlpatterns = [
    path('', views.documents_list, name='documents_list'),
    path('<int:document_id>/', views.document_detail, name='document_detail'),
    path('<int:document_id>/download/', views.document_download, name='document_download'),
    path('<int:document_id>/download/<int:version_number>/', views.document_download, name='document_download_version'),
    path('api/search/', views.document_search_api, name='document_search_api'),
]


