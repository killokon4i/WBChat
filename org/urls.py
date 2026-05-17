from django.urls import path
from . import views

urlpatterns = [
    path('', views.directory, name='directory'),
    path('employee/<int:user_id>/', views.employee_card, name='employee_card'),
    path('employee/<int:user_id>/unban-comments/', views.unban_comments, name='unban_comments'),
    path('department/<int:department_id>/', views.department_view, name='department_view'),
    
    # API
    path('api/tree/', views.org_tree_api, name='org_tree_api'),
    path('api/search/', views.search_employees_api, name='search_employees_api'),
    path('api/birthdays/', views.birthdays_api, name='birthdays_api'),
]


