from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from chats.models import Chat
from notes.models import PersonalNote

from .forms import AccountSettingsForm, DeletePrivateDataForm, SignupForm
from .models import User


@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def signup(request):
    if not django_settings.FEMAKTIV_SIGNUP_ENABLED:
        return render(request, "accounts/signup_closed.html", status=403)
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
        account = form.save(commit=False)
        # Approval and authentication fields may have changed since this request
        # loaded its user. A profile edit must only write its own field.
        account.save(update_fields=["display_name"])
        messages.success(request, _("Your display name has been updated."))
        return redirect("accounts:settings")
    return render(request, "accounts/settings.html", {"form": form})


@login_required
@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def delete_private_data(request):
    form = DeletePrivateDataForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            owner = User.objects.select_for_update().get(pk=request.user.pk)
            Chat.objects.filter(owner=owner).delete()
            PersonalNote.objects.filter(owner=owner).delete()
        messages.success(request, _("Your chats, attached copies, and notes have been deleted."))
        return redirect("accounts:settings")
    return render(
        request,
        "accounts/confirm_delete_data.html",
        {"form": form},
        status=400 if request.method == "POST" else 200,
    )
