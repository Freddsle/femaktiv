from django.urls import path

from . import views

app_name = "pages"
urlpatterns = [
    path("", views.home, name="home"),
    path("community/", views.community, name="community"),
    path("community/<slug:slug>/", views.question, name="question"),
    path("examples/<slug:slug>/", views.example, name="example"),
]
