from django.urls import path

from . import views

app_name = "vocab"

urlpatterns = [
    path("", views.card_list, name="list"),
    path("new/", views.card_create, name="create"),
    path("add/", views.card_add_api, name="add"),
    path("review/", views.review, name="review"),
    path("<int:pk>/edit/", views.card_edit, name="edit"),
    path("<int:pk>/delete/", views.card_delete, name="delete"),
    path("<int:pk>/relearn/", views.card_relearn, name="relearn"),
    path("<int:pk>/answer/", views.card_answer, name="answer"),
]
