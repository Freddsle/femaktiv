from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _

from .views import change_language, entry, health

admin.site.site_header = _("femaktiv administration")
admin.site.site_title = "femaktiv"

urlpatterns = [
    path("", entry, name="entry"),
    path("language/", change_language, name="set_language"),
    path("health/", health, name="health"),
]
urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("notes/", include("notes.urls")),
    path("", include("chats.urls")),
    path("", include("pages.urls")),
    prefix_default_language=True,
)
