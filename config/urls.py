from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="library:list", permanent=False)),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),
    path("texts/", include("library.urls")),
    path("dictionaries/", include("dictionary.urls")),
    path("vocab/", include("vocab.urls")),
]
