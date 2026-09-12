from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from .models import User


class SignupForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("display_name", "email")
        widgets = {
            "display_name": forms.TextInput(attrs={"autocomplete": "nickname"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email address already exists."))
        return email


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )

    error_messages = {
        "invalid_login": _("Please enter a correct email address and password."),
        "inactive": _("This account is inactive."),
    }

    def clean_username(self):
        return User.objects.normalize_email(self.cleaned_data["username"])


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name",)
        widgets = {"display_name": forms.TextInput(attrs={"autocomplete": "nickname"})}


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
