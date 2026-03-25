import hashlib
import re

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
    normalized_email = User._default_manager.normalize_email((email or "").strip()).lower()
    if not normalized_email:
        return False

    queryset = User._default_manager.filter(email__iexact=normalized_email)
    if exclude_user_id is not None:
        queryset = queryset.exclude(pk=exclude_user_id)
    return queryset.exists()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="E-mail",
        help_text="Use um e-mail valido. Ele sera seu acesso ao sistema.",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
                "inputmode": "email",
                "placeholder": "voce@empresa.com",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("email", "password1", "password2")
        labels = {
            "password1": "Senha",
            "password2": "Confirmar senha",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = (
            "Defina a senha que sera usada depois da aprovacao do administrador."
        )
        self.fields["password2"].help_text = "Repita a senha para confirmar."
        style_form_fields(self)

    def clean_email(self):
        email = User._default_manager.normalize_email(
            (self.cleaned_data.get("email") or "").strip()
        ).lower()
        if email_in_use(email):
            raise forms.ValidationError("Ja existe um cadastro com este e-mail.")
        return email

    @staticmethod
    def build_username_from_email(email):
        normalized = User._default_manager.normalize_email((email or "").strip()).lower()
        if not normalized:
            raise forms.ValidationError("Informe um e-mail valido.")

        if len(normalized) <= 150 and not User._default_manager.filter(
            username__iexact=normalized
        ).exists():
            return normalized

        local_part = normalized.split("@", 1)[0]
        base = re.sub(r"[^a-z0-9@.+_-]+", "-", local_part.lower()).strip("-._") or "user"

        index = 1
        while True:
            digest = hashlib.sha1(f"{normalized}-{index}".encode("utf-8")).hexdigest()[:10]
            candidate = f"{base[:139]}-{digest}"[:150]
            if not User._default_manager.filter(username__iexact=candidate).exists():
                return candidate
            index += 1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.build_username_from_email(self.cleaned_data["email"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class StyledAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive": "Seu cadastro foi recebido e aguarda validacao do administrador.",
    }

    username = forms.EmailField(
        label="E-mail",
        help_text="Entre com o mesmo e-mail aprovado no cadastro.",
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
                "inputmode": "email",
                "placeholder": "voce@empresa.com",
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
        username = User._default_manager.normalize_email(
            (self.cleaned_data.get("username") or "").strip()
        ).lower()
        password = self.cleaned_data.get("password")

        if username is not None and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password,
            )
            if self.user_cache is None:
                user = User._default_manager.filter(email__iexact=username).first()
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
