from django.contrib import admin

from shopping.models import ShoppingItem


@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "quantity", "unit_price", "is_purchased", "updated_at")
    list_filter = ("is_purchased",)
    search_fields = ("title", "notes", "user__username")
