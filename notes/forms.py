from django import forms
from django.utils.translation import gettext_lazy as _

from .models import PersonalNote


class PersonalNoteForm(forms.ModelForm):
    class Meta:
        model = PersonalNote
        fields = ("title", "body")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": _("For example: My food preferences")}),
            "body": forms.Textarea(
                attrs={
                    "rows": 9,
                    "placeholder": _("Write what you would like to keep for future chats."),
                }
            ),
        }
