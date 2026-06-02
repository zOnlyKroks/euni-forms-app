"""URL routes for the EVE Uni Forms app."""

# Django
from django.urls import path

# AA EVE Uni Forms
from euniforms import views

app_name = "euniforms"

urlpatterns = [
    # Member-facing
    path("", views.index, name="index"),
    path("form/<int:form_pk>/", views.form_fill, name="form_fill"),
    path("form/<int:form_pk>/submitted/", views.form_submitted, name="form_submitted"),
    # Form management
    path("manage/new/", views.form_create, name="form_create"),
    path("manage/<int:form_pk>/edit/", views.form_edit, name="form_edit"),
    path("manage/<int:form_pk>/delete/", views.form_delete, name="form_delete"),
    path("manage/<int:form_pk>/fields/", views.manage_fields, name="manage_fields"),
    path("manage/<int:form_pk>/fields/add/", views.field_create, name="field_create"),
    path("manage/field/<int:field_pk>/edit/", views.field_edit, name="field_edit"),
    path("manage/field/<int:field_pk>/delete/", views.field_delete, name="field_delete"),
    path(
        "manage/field/<int:field_pk>/move/<str:direction>/",
        views.field_move,
        name="field_move",
    ),
    # Collaborators
    path("manage/<int:form_pk>/collaborators/", views.collaborators_list, name="collaborators_list"),
    path("manage/<int:form_pk>/collaborators/add/", views.collaborator_add, name="collaborator_add"),
    path(
        "manage/<int:form_pk>/collaborators/<int:user_id>/remove/",
        views.collaborator_remove,
        name="collaborator_remove",
    ),
    # Responses
    path("manage/<int:form_pk>/responses/", views.responses_list, name="responses_list"),
    path("manage/<int:form_pk>/responses.csv", views.responses_csv, name="responses_csv"),
    path(
        "manage/response/<int:response_pk>/",
        views.response_detail,
        name="response_detail",
    ),
    path(
        "manage/response/<int:response_pk>/delete/",
        views.response_delete,
        name="response_delete",
    ),
]
