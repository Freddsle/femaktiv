from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_safe

from .forms import PersonalNoteForm
from .models import PersonalNote


@login_required
@require_safe
def note_list(request):
    notes = PersonalNote.objects.filter(owner=request.user)
    return render(request, "notes/list.html", {"notes": notes})


@login_required
@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def create(request):
    form = PersonalNoteForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        note = form.save(commit=False)
        note.owner = request.user
        note.save()
        messages.success(request, _("Your note has been saved."))
        return redirect("notes:list")
    return render(request, "notes/form.html", {"form": form})


@login_required
@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def edit(request, pk):
    note = get_object_or_404(PersonalNote, pk=pk, owner=request.user)
    form = PersonalNoteForm(request.POST if request.method == "POST" else None, instance=note)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Your note has been updated."))
        return redirect("notes:list")
    return render(request, "notes/form.html", {"form": form, "note": note})


@login_required
@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def delete(request, pk):
    note = get_object_or_404(PersonalNote, pk=pk, owner=request.user)
    if request.method == "POST":
        note.delete()
        messages.success(request, _("Your note has been deleted."))
        return redirect("notes:list")
    return render(request, "notes/confirm_delete.html", {"note": note})
