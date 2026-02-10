from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import Account
from goals.models import SavingGoal
from transactions.models import Transaction


MONTH_NAMES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Marco",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


class DashboardContextMixin(LoginRequiredMixin):
    expense_palette = ["#0b0b0f", "#7abf00", "#d1d5db", "#9ca3af", "#fb7185"]

    def _shift_month(self, base_month: date, offset: int) -> date:
        serial = base_month.year * 12 + (base_month.month - 1) + offset
        year, month_idx = divmod(serial, 12)
        return date(year, month_idx + 1, 1)

    def _get_selected_month(self) -> date:
        today = timezone.localdate()
        selected_value = (self.request.GET.get("month") or "").strip()

        if not selected_value:
            return today.replace(day=1)

        try:
            year_str, month_str = selected_value.split("-", maxsplit=1)
            year = int(year_str)
            month = int(month_str)
            if month < 1 or month > 12:
                raise ValueError
            return date(year, month, 1)
        except (TypeError, ValueError):
            return today.replace(day=1)

    def _build_month_navigation(self, selected_month: date):
        prev_month = self._shift_month(selected_month, -1)
        next_month = self._shift_month(selected_month, 1)

        prev_params = self.request.GET.copy()
        prev_params["month"] = f"{prev_month.year:04d}-{prev_month.month:02d}"

        next_params = self.request.GET.copy()
        next_params["month"] = f"{next_month.year:04d}-{next_month.month:02d}"

        selected_label = f"{MONTH_NAMES_PT.get(selected_month.month, '')} {selected_month.year}"
        return selected_label, prev_params.urlencode(), next_params.urlencode()

    def _build_expense_chart(self, current_month_transactions, monthly_expense):
        expense_rows = list(
            current_month_transactions.filter(
                transaction_type=Transaction.TransactionType.EXPENSE
            )
            .values("category__name")
            .annotate(total=Coalesce(Sum("amount"), Decimal("0.00")))
            .order_by("-total")
        )

        if monthly_expense <= 0:
            return [], "conic-gradient(#2b2f3a 0 100%)"

        segments = []
        running_total = Decimal("0.00")
        top_rows = expense_rows[:4]

        for idx, row in enumerate(top_rows):
            amount = row["total"] or Decimal("0.00")
            if amount <= 0:
                continue
            running_total += amount
            segments.append(
                {
                    "name": row["category__name"] or "Sem categoria",
                    "total": amount,
                    "color": self.expense_palette[idx % len(self.expense_palette)],
                }
            )

        remainder = monthly_expense - running_total
        if remainder > 0:
            segments.append(
                {
                    "name": "Outros",
                    "total": remainder,
                    "color": self.expense_palette[len(segments) % len(self.expense_palette)],
                }
            )

        total_float = float(monthly_expense)
        cursor = 0.0
        stops = []
        for segment in segments:
            percent = (float(segment["total"]) / total_float) * 100
            end = cursor + percent
            segment["percent"] = percent
            stops.append(f"{segment['color']} {cursor:.2f}% {end:.2f}%")
            cursor = end

        if cursor < 100:
            stops.append(f"#2b2f3a {cursor:.2f}% 100%")

        return segments, f"conic-gradient({', '.join(stops)})"

    def get_dashboard_context(self):
        user = self.request.user
        today = timezone.localdate()
        selected_month = self._get_selected_month()

        current_month_transactions = Transaction.objects.filter(
            user=user,
            date__year=selected_month.year,
            date__month=selected_month.month,
        )

        monthly_income = current_month_transactions.filter(
            transaction_type=Transaction.TransactionType.INCOME
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        monthly_expense = current_month_transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        initial_total = Account.objects.filter(user=user, is_active=True).aggregate(
            total=Coalesce(Sum("initial_balance"), Decimal("0.00"))
        )["total"]

        available_transactions = Transaction.objects.filter(
            user=user,
            is_cleared=True,
            date__lte=today,
        )

        total_income = available_transactions.filter(
            transaction_type=Transaction.TransactionType.INCOME,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        total_expense = available_transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        latest_transactions = (
            Transaction.objects.filter(user=user)
            .select_related("account", "category", "destination_account")
            .order_by("-date", "-created_at")[:6]
        )

        due_window_end = today + timedelta(days=30)
        due_notifications_qs = (
            Transaction.objects.filter(
                user=user,
                transaction_type=Transaction.TransactionType.EXPENSE,
                is_cleared=False,
                date__lte=due_window_end,
            )
            .select_related("account", "category")
            .order_by("date", "created_at")
        )
        due_notifications_count = due_notifications_qs.count()
        due_overdue_count = due_notifications_qs.filter(date__lt=today).count()
        due_notifications = list(due_notifications_qs[:6])

        pending_expenses = current_month_transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE,
            is_cleared=False,
        )

        pending_expense_total = pending_expenses.aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]
        pending_expense_count = pending_expenses.count()

        expense_categories, expense_donut_style = self._build_expense_chart(
            current_month_transactions,
            monthly_expense,
        )

        active_goal = (
            SavingGoal.objects.filter(user=user, is_active=True)
            .order_by("-updated_at", "-created_at")
            .first()
        )

        goal_saved = Decimal("0.00")
        goal_target = Decimal("0.00")
        goal_progress = Decimal("0.00")
        goal_remaining = Decimal("0.00")

        if active_goal:
            goal_saved = active_goal.total_saved
            goal_target = active_goal.target_amount
            goal_progress = active_goal.progress_percent
            goal_remaining = active_goal.remaining_amount

        selected_month_label, prev_month_query, next_month_query = self._build_month_navigation(
            selected_month
        )

        return {
            "total_balance": initial_total + total_income - total_expense,
            "monthly_income": monthly_income,
            "monthly_expense": monthly_expense,
            "latest_transactions": latest_transactions,
            "selected_month_label": selected_month_label,
            "prev_month_query": prev_month_query,
            "next_month_query": next_month_query,
            "today": today,
            "pending_expense_total": pending_expense_total,
            "pending_expense_count": pending_expense_count,
            "due_notifications": due_notifications,
            "due_notifications_count": due_notifications_count,
            "due_overdue_count": due_overdue_count,
            "expense_categories": expense_categories,
            "expense_donut_style": expense_donut_style,
            "active_goal": active_goal,
            "goal_saved": goal_saved,
            "goal_target": goal_target,
            "goal_progress": goal_progress,
            "goal_remaining": goal_remaining,
        }


class DashboardHomeView(DashboardContextMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_context())
        return context


class DashboardSummaryPartialView(DashboardContextMixin, TemplateView):
    template_name = "dashboard/partials/summary_cards.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_context())
        return context


class DashboardLatestPartialView(DashboardContextMixin, TemplateView):
    template_name = "dashboard/partials/latest_transactions.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_context())
        return context
