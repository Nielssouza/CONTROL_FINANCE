from django import forms

from accounts.models import Account
from common.forms import style_form_fields


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("name", "account_type", "initial_balance", "is_active")
        labels = {
            "name": "Nome da conta",
            "account_type": "Tipo",
            "initial_balance": "Saldo inicial",
            "is_active": "Conta ativa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form_fields(self)
