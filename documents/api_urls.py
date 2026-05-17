from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'categories', api_views.DocumentCategoryViewSet, basename='document-category')
router.register(r'documents', api_views.DocumentViewSet, basename='document')
router.register(r'acknowledgements', api_views.DocumentAcknowledgementViewSet, basename='acknowledgement')

urlpatterns = [
    path('', include(router.urls)),
]


