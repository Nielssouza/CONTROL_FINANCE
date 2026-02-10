import re
from decimal import Decimal, InvalidOperation

from django import forms

from common.forms import style_form_fields
from goals.models import GoalEntry, SavingGoal


class GoalForm(forms.ModelForm):
    target_amount = forms.CharField(
        label="Valor alvo",
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "R$ 0,00",
            }
        ),
    )

    class Meta:
        model = SavingGoal
        fields = ("name", "target_amount", "target_date", "is_active")
        labels = {
            "name": "Nome do objetivo",
            "target_date": "Data alvo",
            "is_active": "Ativo",
        }
        widgets = {
            "target_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["target_amount"] = f"{self.instance.target_amount:.2f}"
        style_form_fields(self)

    def clean_target_amount(self):
        raw_value = (self.cleaned_data.get("target_amount") or "").strip()
        if not raw_value:
            raise forms.ValidationError("Informe um valor alvo maior que zero.")

        normalized = raw_value.replace("R$", "").replace(" ", "")
        normalized = normalized.replace("\u00a0", "")
        normalized = re.sub(r"[^\d,.-]", "", normalized)

        if "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")

        try:
            value = Decimal(normalized)
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Informe um valor alvo valido.")

        if value <= 0:
            raise forms.ValidationError("Informe um valor alvo maior que zero.")

        return value.quantize(Decimal("0.01"))


class GoalEntryForm(forms.ModelForm):
    amount = forms.CharField(
        label="Valor do lancamento",
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "R$ 0,00",
            }
        ),
    )

    class Meta:
        model = GoalEntry
        fields = ("amount", "date", "description")
        labels = {
            "date": "Data",
            "description": "Descricao",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form_fields(self)

    def clean_amount(self):
        raw_value = (self.cleaned_data.get("amount") or "").strip()
        if not raw_value:
            raise forms.ValidationError("Informe um valor maior que zero.")

        normalized = raw_value.replace("R$", "").replace(" ", "")
        normalized = normalized.replace("\u00a0", "")
        normalized = re.sub(r"[^\d,.-]", "", normalized)

        if "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")

        try:
            value = Decimal(normalized)
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Informe um valor valido.")

        if value <= 0:
            raise forms.ValidationError("Informe um valor maior que zero.")

        return value.quantize(Decimal("0.01"))