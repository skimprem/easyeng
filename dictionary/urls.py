from django.urls import path

from . import views

app_name = "dictionary"

urlpatterns = [
    path("lookup/", views.lookup_view, name="lookup"),
    path("", views.dictionary_list, name="list"),
    path("<int:pk>/toggle/", views.dictionary_toggle, name="toggle"),
    path("<int:pk>/delete/", views.dictionary_delete, name="delete"),
    path("freedict/", views.freedict_catalog, name="freedict"),
]
