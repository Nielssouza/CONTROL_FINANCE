from django.contrib import admin

from goals.models import GoalEntry, SavingGoal


@admin.register(SavingGoal)
class SavingGoalAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "target_amount", "is_active", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "user__username")


@admin.register(GoalEntry)
class GoalEntryAdmin(admin.ModelAdmin):
    list_display = ("goal", "user", "amount", "date", "created_at")
    list_filter = ("date", "created_at")
    search_fields = ("goal__name", "user__username", "description")