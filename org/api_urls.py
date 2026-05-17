from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'departments', api_views.DepartmentViewSet, basename='department')
router.register(r'positions', api_views.PositionViewSet, basename='position')
router.register(r'employees', api_views.EmployeeViewSet, basename='employee')
router.register(r'status-logs', api_views.EmployeeStatusLogViewSet, basename='status-log')

urlpatterns = [
    path('', include(router.urls)),
]


