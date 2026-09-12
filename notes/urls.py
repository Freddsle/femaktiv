from django.urls import path

from . import views

app_name = "notes"

urlpatterns = [
    path("", views.note_list, name="list"),
    path("new/", views.create, name="create"),
    path("<uuid:pk>/edit/", views.edit, name="edit"),
    path("<uuid:pk>/delete/", views.delete, name="delete"),
]
