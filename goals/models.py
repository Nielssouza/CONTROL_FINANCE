from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from common.tenancy import assign_tenant


class SavingGoal(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saving_goals",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="saving_goals",
        null=True,
        blank=True,
    )
    name = models.CharField("Nome", max_length=120)
    target_amount = models.DecimalField("Valor alvo", max_digits=12, decimal_places=2)
    target_date = models.DateField("Data alvo", null=True, blank=True)
    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ("-is_active", "-updated_at")
        verbose_name = "Objetivo"
        verbose_name_plural = "Objetivos"

    def __str__(self):
        return f"{self.name} - R$ {self.target_amount}"

    @property
    def total_saved(self) -> Decimal:
        return self.entries.aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]

    @property
    def progress_percent(self) -> Decimal:
        if self.target_amount <= 0:
            return Decimal("0.00")

        percent = (self.total_saved / self.target_amount) * Decimal("100")
        return min(percent, Decimal("100.00"))

    @property
    def remaining_amount(self) -> Decimal:
        remaining = self.target_amount - self.total_saved
        return remaining if remaining > 0 else Decimal("0.00")

    def clean(self):
        if self.target_amount <= 0:
            raise ValidationError({"target_amount": "Informe um valor alvo maior que zero."})

    def save(self, *args, **kwargs):
        assign_tenant(self)
        self.full_clean()
        return super().save(*args, **kwargs)


class GoalEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goal_entries",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="goal_entries",
        null=True,
        blank=True,
    )
    goal = models.ForeignKey(
        SavingGoal,
        on_delete=models.CASCADE,
        related_name="entries",
        verbose_name="Objetivo",
    )
    amount = models.DecimalField("Valor", max_digits=12, decimal_places=2)
    date = models.DateField("Data", default=timezone.localdate)
    description = models.CharField("Descricao", max_length=255, blank=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        ordering = ("-date", "-created_at")
        verbose_name = "Lancamento do objetivo"
        verbose_name_plural = "Lancamentos do objetivo"
        indexes = [
            models.Index(fields=("tenant", "date")),
            models.Index(fields=("goal", "date")),
        ]

    def __str__(self):
        return f"{self.goal.name} - R$ {self.amount}"

    def clean(self):
        assign_tenant(self)
        if self.amount <= 0:
            raise ValidationError({"amount": "Informe um valor maior que zero."})

        if self.goal_id and self.tenant_id and self.goal.tenant_id != self.tenant_id:
            raise ValidationError({"goal": "Objetivo invalido para este cliente."})

    def save(self, *args, **kwargs):
        assign_tenant(self)
        self.full_clean()
        return super().save(*args, **kwargs)
