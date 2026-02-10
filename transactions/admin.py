from django.contrib import admin

from transactions.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "transaction_type",
        "amount",
        "account",
        "destination_account",
        "category",
        "user",
    )
    list_filter = ("transaction_type", "date", "recurrence_type")
    search_fields = ("description", "account__name", "user__username")
