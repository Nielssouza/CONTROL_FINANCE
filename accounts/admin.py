from django.contrib import admin

from accounts.models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "user", "initial_balance", "is_active")
    list_filter = ("account_type", "is_active")
    search_fields = ("name", "user__username")
