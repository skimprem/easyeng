from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    path("", views.text_list, name="list"),
    path("new/", views.text_create, name="create"),
    path("upload/", views.text_upload, name="upload"),
    path("preview/", views.markdown_preview, name="preview"),
    path("gutenberg/", views.gutenberg_search, name="gutenberg"),
    path("gutenberg/import/", views.gutenberg_import, name="gutenberg_import"),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:pk>/", views.share_respond, name="share_respond"),
    path("<int:pk>/", views.text_read, name="read"),
    path("<int:pk>/edit/", views.text_edit, name="edit"),
    path("<int:pk>/delete/", views.text_delete, name="delete"),
    path("<int:pk>/share/", views.text_share, name="share"),
    path("<int:pk>/progress/", views.text_progress, name="progress"),
    path("<int:pk>/glosses/", views.text_glosses, name="glosses"),
]
