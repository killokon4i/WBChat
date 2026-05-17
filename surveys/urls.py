from django.urls import path

from . import views

urlpatterns = [
    path("", views.survey_list, name="surveys_list"),
    path("manage/", views.survey_manage_list, name="surveys_manage_list"),
    path("manage/bulk/", views.survey_manage_bulk, name="surveys_manage_bulk"),
    path("archive/", views.survey_archive_list, name="surveys_archive_list"),
    path("archive/bulk/", views.survey_archive_bulk, name="surveys_archive_bulk"),
    path("create/", views.survey_create, name="surveys_create"),
    path("<int:pk>/edit/", views.survey_edit, name="surveys_edit"),
    path("<int:pk>/launch/", views.survey_launch, name="surveys_launch"),
    path("<int:pk>/close/", views.survey_close, name="surveys_close"),
    path("<int:pk>/archive/", views.survey_archive, name="surveys_archive"),
    path("<int:pk>/take/", views.survey_take, name="surveys_take"),
    path("<int:pk>/results/", views.survey_results, name="surveys_results"),
    path(
        "<int:pk>/results/user/<int:user_id>/",
        views.survey_results_user,
        name="surveys_results_user",
    ),
]

