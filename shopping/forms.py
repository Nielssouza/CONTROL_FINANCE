from django import forms

from common.forms import style_form_fields
from shopping.models import ShoppingItem


class ShoppingItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingItem
        fields = ("title", "quantity", "unit_price", "notes", "is_purchased")
        labels = {
            "title": "Item",
            "quantity": "Quantidade",
            "unit_price": "Preco unitario estimado",
            "notes": "Observacao",
            "is_purchased": "Ja comprado",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form_fields(self)
        self.fields["quantity"].widget.attrs.update({"min": "1", "step": "1"})
        self.fields["unit_price"].widget.attrs.update({"min": "0", "step": "0.01"})
        self.fields["unit_price"].required = False
