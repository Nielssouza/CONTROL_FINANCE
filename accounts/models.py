from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone


class Account(models.Model):
    class AccountType(models.TextChoices):
        BANK = "bank", "Banco"
        CASH = "cash", "Dinheiro"
        CARD = "card", "Cartao"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts",
    )
    name = models.CharField("Nome", max_length=120)
    account_type = models.CharField(
        "Tipo",
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.BANK,
    )
    initial_balance = models.DecimalField(
        "Saldo inicial",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField("Criada em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizada em", auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Conta"
        verbose_name_plural = "Contas"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "name"), name="unique_account_name_per_user"
            )
        ]

    def __str__(self):
        return self.name

    @property
    def balance(self) -> Decimal:
        today = timezone.localdate()

        posted_transactions = self.transactions.filter(
            is_cleared=True,
            is_ignored=False,
            date__lte=today,
        )
        income = posted_transactions.filter(transaction_type="income").aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]
        expenses = posted_transactions.filter(transaction_type="expense").aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]
        outgoing_transfers = posted_transactions.filter(
            transaction_type="transfer"
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        incoming_transfers = self.incoming_transfers.filter(
            transaction_type="transfer",
            is_cleared=True,
            is_ignored=False,
            date__lte=today,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        return (
            self.initial_balance
            + income
            + incoming_transfers
            - expenses
            - outgoing_transfers
        )


