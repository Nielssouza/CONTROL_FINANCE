from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class ShoppingItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shopping_items",
    )
    title = models.CharField("Item", max_length=140)
    quantity = models.PositiveIntegerField(
        "Quantidade",
        default=1,
        validators=[MinValueValidator(1)],
    )
    unit_price = models.DecimalField(
        "Preco unitario estimado",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    notes = models.CharField("Observacao", max_length=220, blank=True)
    is_purchased = models.BooleanField("Comprado", default=False)
    purchased_at = models.DateTimeField("Comprado em", null=True, blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ("is_purchased", "-updated_at", "-created_at")
        verbose_name = "Item de compra"
        verbose_name_plural = "Itens de compra"
        indexes = [
            models.Index(fields=("user", "is_purchased", "updated_at")),
            models.Index(fields=("user", "created_at")),
        ]

    def __str__(self):
        return self.title

    @property
    def estimated_total(self) -> Decimal:
        if self.unit_price is None:
            return Decimal("0.00")
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))

    def toggle_purchased(self):
        self.is_purchased = not self.is_purchased
        self.purchased_at = timezone.now() if self.is_purchased else None
    def save(self, *args, **kwargs):
        if self.is_purchased and self.purchased_at is None:
            self.purchased_at = timezone.now()
        if not self.is_purchased:
            self.purchased_at = None
        return super().save(*args, **kwargs)
