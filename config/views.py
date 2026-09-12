from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import override
from django.views.decorators.cache import never_cache
from django.views.i18n import set_language


@never_cache
def entry(request):
    language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, "en")
    if language not in {"en", "de"}:
        language = "en"
    return HttpResponseRedirect(f"/{language}/")


def change_language(request):
    # The unprefixed endpoint may inherit a browser/cookie locale different from
    # the current page. Resolve that page using its URL locale before translating.
    source_language = "en"
    for candidate in (
        request.POST.get("next", request.GET.get("next", "")),
        request.META.get("HTTP_REFERER", ""),
    ):
        if url_has_allowed_host_and_scheme(
            candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            prefix = urlsplit(candidate).path.strip("/").split("/")[0]
            if prefix in {"en", "de"}:
                source_language = prefix
            break
    with override(source_language):
        return set_language(request)


def csrf_failure(request, reason=""):
    if "/api/" in request.path:
        return JsonResponse(
            {
                "error": {
                    "code": "csrf_failed",
                    "message": _(
                        "Your session could not be verified. Refresh the page and try again."
                    ),
                }
            },
            status=403,
        )
    return render(request, "errors/403.html", status=403)


def health(request):
    return JsonResponse({"status": "ok", "mode": "placeholder", "version": "0.1.0"})
