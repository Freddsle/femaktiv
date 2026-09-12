from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .forms import AccountSettingsForm, SignupForm


@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("chats:list")
    form = SignupForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("chats:list")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def settings(request):
    form = AccountSettingsForm(
        request.POST if request.method == "POST" else None, instance=request.user
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Your display name has been updated."))
        return redirect("accounts:settings")
    return render(request, "accounts/settings.html", {"form": form})
