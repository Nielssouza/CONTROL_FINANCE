from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
    UsernameField,
)
from django.core.exceptions import ValidationError

from common.forms import style_form_fields


User = get_user_model()


def email_in_use(email, *, exclude_user_id=None):
    normalized_email = (email or "").strip()
    if not normalized_email:
        return False

    queryset = User._default_manager.filter(email__iexact=normalized_email)
    if exclude_user_id is not None:
        queryset = queryset.exclude(pk=exclude_user_id)
    return queryset.exists()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-mail")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {
            "username": "Usuario",
            "password1": "Senha",
            "password2": "Confirmar senha",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form_fields(self)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email_in_use(email):
            raise forms.ValidationError("Ja existe um cadastro com este e-mail.")
        return email


class StyledAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive": "Seu cadastro foi recebido e aguarda validacao do administrador.",
    }

    username = UsernameField(
        label="Usuario",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form_fields(self)

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password,
            )
            if self.user_cache is None:
                user = User._default_manager.filter(username__iexact=username).first()
                if user is not None and not user.is_active and user.check_password(password):
                    raise ValidationError(
                        self.error_messages["inactive"],
                        code="inactive",
                    )
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class AdminUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-mail")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email_in_use(email):
            raise forms.ValidationError("Ja existe um cadastro com este e-mail.")
        return email


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and email_in_use(email, exclude_user_id=self.instance.pk):
            raise forms.ValidationError("Ja existe um cadastro com este e-mail.")
        return email
