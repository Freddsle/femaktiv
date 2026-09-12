from django.urls import path

from . import views

app_name = "chats"
urlpatterns = [
    path("chats/", views.chat_list, name="list"),
    path("chats/new/", views.create, name="create"),
    path("chats/<uuid:pk>/", views.detail, name="detail"),
    path("chats/<uuid:pk>/rename/", views.rename, name="rename"),
    path("chats/<uuid:pk>/delete/", views.delete, name="delete"),
    path("api/chats/<uuid:pk>/messages/", views.send_message, name="send"),
]
