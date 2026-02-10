from calendar import monthrange
from datetime import date as date_cls
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = "income", "Receita"
        EXPENSE = "expense", "Despesa"
        TRANSFER = "transfer", "Transferencia"

    class RecurrenceType(models.TextChoices):
        FIXED = "fixed", "Fixa"
        MONTHLY = "monthly", "Mensal"
        QUARTERLY = "quarterly", "Trimestral"
        YEARLY = "yearly", "Anual"
        INSTALLMENT = "installment", "Parcelado"

    RECURRING_HORIZON_MONTHS = 60

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        "Tipo",
        max_length=20,
        choices=TransactionType.choices,
    )
    amount = models.DecimalField("Valor", max_digits=12, decimal_places=2)
    date = models.DateField("Data", default=timezone.localdate)
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Conta de origem",
    )
    destination_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="incoming_transfers",
        null=True,
        blank=True,
        verbose_name="Conta de destino",
    )
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        related_name="transactions",
        null=True,
        blank=True,
        verbose_name="Categoria",
    )
    description = models.CharField("Descricao", max_length=255, blank=True)
    is_cleared = models.BooleanField(
        "Baixada",
        default=False,
        help_text="Marque quando a transacao ja foi recebida/paga.",
    )

    recurrence_type = models.CharField(
        "Recorrencia",
        max_length=20,
        choices=RecurrenceType.choices,
        default=RecurrenceType.FIXED,
    )
    recurrence_interval = models.PositiveSmallIntegerField(
        "Intervalo de recorrencia",
        default=1,
        help_text="Preparado para futura automacao de recorrencias.",
    )
    installment_count = models.PositiveSmallIntegerField(
        "Quantidade de parcelas",
        null=True,
        blank=True,
        help_text="Informe apenas quando a recorrencia for Parcelado.",
    )

    created_at = models.DateTimeField("Criada em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizada em", auto_now=True)

    class Meta:
        ordering = ("-date", "-created_at")
        verbose_name = "Transacao"
        verbose_name_plural = "Transacoes"
        indexes = [
            models.Index(fields=("user", "date")),
            models.Index(fields=("user", "transaction_type")),
            models.Index(fields=("user", "is_cleared", "date")),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - R$ {self.amount}"

    @property
    def signed_amount(self) -> Decimal:
        if self.transaction_type == self.TransactionType.EXPENSE:
            return -self.amount
        return self.amount

    @staticmethod
    def _add_months_safe(base_date: date_cls, month_delta: int) -> date_cls:
        serial = base_date.year * 12 + (base_date.month - 1) + month_delta
        target_year, target_month_idx = divmod(serial, 12)
        target_month = target_month_idx + 1
        target_day = min(base_date.day, monthrange(target_year, target_month)[1])
        return date_cls(target_year, target_month, target_day)

    def _recurrence_plan(self):
        interval = max(1, self.recurrence_interval or 1)

        if self.recurrence_type in {
            self.RecurrenceType.FIXED,
            self.RecurrenceType.MONTHLY,
        }:
            step_months = interval
            count = self.RECURRING_HORIZON_MONTHS // step_months
            return step_months, count

        if self.recurrence_type == self.RecurrenceType.QUARTERLY:
            step_months = 3 * interval
            count = self.RECURRING_HORIZON_MONTHS // step_months
            return step_months, count

        if self.recurrence_type == self.RecurrenceType.YEARLY:
            step_months = 12 * interval
            count = self.RECURRING_HORIZON_MONTHS // step_months
            return step_months, count

        if self.recurrence_type == self.RecurrenceType.INSTALLMENT:
            step_months = interval
            total_installments = max(1, self.installment_count or 1)
            count = max(0, total_installments - 1)
            return step_months, count

        return 0, 0

    def _occurrence_exists(self, target_date: date_cls) -> bool:
        return Transaction.objects.filter(
            user=self.user,
            transaction_type=self.transaction_type,
            amount=self.amount,
            date=target_date,
            account=self.account,
            destination_account=self.destination_account,
            category=self.category,
            description=self.description,
            recurrence_type=self.recurrence_type,
            recurrence_interval=self.recurrence_interval,
            installment_count=self.installment_count,
        ).exclude(pk=self.pk).exists()

    def generate_future_occurrences(self) -> int:
        if not self.pk:
            return 0

        step_months, count = self._recurrence_plan()
        if step_months <= 0 or count <= 0:
            return 0

        upcoming_rows = []
        for index in range(1, count + 1):
            target_date = self._add_months_safe(self.date, step_months * index)
            if self._occurrence_exists(target_date):
                continue

            upcoming_rows.append(
                Transaction(
                    user=self.user,
                    transaction_type=self.transaction_type,
                    amount=self.amount,
                    date=target_date,
                    account=self.account,
                    destination_account=self.destination_account,
                    category=self.category,
                    description=self.description,
                    is_cleared=False,
                    recurrence_type=self.recurrence_type,
                    recurrence_interval=self.recurrence_interval,
                    installment_count=self.installment_count,
                )
            )

        if not upcoming_rows:
            return 0

        Transaction.objects.bulk_create(upcoming_rows)
        return len(upcoming_rows)

    def clean(self):
        if self.amount <= 0:
            raise ValidationError({"amount": "Informe um valor maior que zero."})

        if self.account and self.account.user_id != self.user_id:
            raise ValidationError({"account": "Conta invalida para este usuario."})

        if self.category and self.category.user_id != self.user_id:
            raise ValidationError({"category": "Categoria invalida para este usuario."})

        if self.destination_account and self.destination_account.user_id != self.user_id:
            raise ValidationError(
                {"destination_account": "Conta de destino invalida para este usuario."}
            )

        if self.recurrence_type == self.RecurrenceType.INSTALLMENT:
            if not self.installment_count or self.installment_count < 2:
                raise ValidationError(
                    {
                        "installment_count": (
                            "Informe a quantidade de parcelas (minimo 2)."
                        )
                    }
                )
        else:
            self.installment_count = None

        if self.transaction_type == self.TransactionType.TRANSFER:
            if not self.destination_account:
                raise ValidationError(
                    {"destination_account": "Transferencias precisam de conta de destino."}
                )
            if self.destination_account == self.account:
                raise ValidationError(
                    {"destination_account": "A conta de destino deve ser diferente da origem."}
                )
            if self.category:
                raise ValidationError(
                    {"category": "Transferencia nao deve possuir categoria."}
                )
        else:
            if self.destination_account:
                raise ValidationError(
                    {
                        "destination_account": (
                            "Conta de destino e permitida apenas para transferencias."
                        )
                    }
                )
            if self.category and self.category.category_type != self.transaction_type:
                raise ValidationError(
                    {"category": "Categoria incompativel com o tipo da transacao."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
