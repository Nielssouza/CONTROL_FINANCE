from django.conf import settings
from django.db import models


class Category(models.Model):
    class CategoryType(models.TextChoices):
        INCOME = "income", "Receita"
        EXPENSE = "expense", "Despesa"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField("Nome", max_length=80)
    category_type = models.CharField(
        "Tipo",
        max_length=20,
        choices=CategoryType.choices,
    )
    created_at = models.DateTimeField("Criada em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizada em", auto_now=True)

    class Meta:
        ordering = ("category_type", "name")
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "name", "category_type"),
                name="unique_category_name_type_per_user",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"
