import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from accounts.models import Account
from common.mixins import UserAssignMixin, UserQuerySetMixin
from transactions.forms import QuickTransactionForm, StatementFilterForm, TransactionForm
from transactions.models import Transaction


class TransactionFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class TransactionCreateView(UserAssignMixin, TransactionFormKwargsMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transactions:statement")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.generate_future_occurrences()
        return response


class TransactionUpdateView(UserQuerySetMixin, TransactionFormKwargsMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transactions:statement")


class TransactionDeleteView(UserQuerySetMixin, DeleteView):
    model = Transaction
    template_name = "transactions/transaction_confirm_delete.html"
    success_url = reverse_lazy("transactions:statement")


class StatementViewBase(LoginRequiredMixin, TemplateView):
    template_name = "transactions/statement.html"

    def get_filter_form(self):
        return StatementFilterForm(self.request.GET, user=self.request.user)

    @staticmethod
    def month_value_to_date(month_value):
        if not month_value:
            return None
        try:
            year, month = month_value.split("-")
            return date(int(year), int(month), 1)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def shift_month(base_month, delta):
        month_index = (base_month.month - 1) + delta
        year = base_month.year + (month_index // 12)
        month = (month_index % 12) + 1
        return date(year, month, 1)

    def get_selected_month(self):
        requested_value = self.request.GET.get("month", "")
        parsed_value = self.month_value_to_date(requested_value)

        if parsed_value:
            return parsed_value, requested_value

        current_month = timezone.localdate().replace(day=1)
        return current_month, current_month.strftime("%Y-%m")

    def apply_filters(self, queryset, form, selected_month, include_query=True):
        account = None
        category = None
        query = ""

        queryset = queryset.filter(
            date__year=selected_month.year,
            date__month=selected_month.month,
        )

        if form.is_valid():
            account = form.cleaned_data.get("account")
            category = form.cleaned_data.get("category")
            query = (form.cleaned_data.get("query") or "").strip()

        if account:
            queryset = queryset.filter(Q(account=account) | Q(destination_account=account))
        if category:
            queryset = queryset.filter(category=category)
        if include_query and query:
            queryset = queryset.filter(
                Q(description__icontains=query)
                | Q(category__name__icontains=query)
                | Q(account__name__icontains=query)
            )

        return queryset

    def get_month_navigation(self, selected_month):
        selected_label = date_format(selected_month, "F Y").capitalize()
        prev_month = self.shift_month(selected_month, -1)
        next_month = self.shift_month(selected_month, 1)

        prev_params = self.request.GET.copy()
        prev_params["month"] = prev_month.strftime("%Y-%m")

        next_params = self.request.GET.copy()
        next_params["month"] = next_month.strftime("%Y-%m")

        return selected_label, prev_params.urlencode(), next_params.urlencode()

    def get_balances(self, form, selected_month):
        user = self.request.user
        today = timezone.localdate()

        initial_total = Account.objects.filter(user=user, is_active=True).aggregate(
            total=Coalesce(Sum("initial_balance"), Decimal("0.00"))
        )["total"]

        available_transactions = Transaction.objects.filter(
            user=user,
            is_cleared=True,
            date__lte=today,
        )
        total_income = available_transactions.filter(
            transaction_type=Transaction.TransactionType.INCOME
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))['total']
        total_expense = available_transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))['total']
        current_balance = initial_total + total_income - total_expense

        monthly_queryset = Transaction.objects.filter(
            user=user,
            date__year=selected_month.year,
            date__month=selected_month.month,
        )

        if form.is_valid():
            account = form.cleaned_data.get("account")
            category = form.cleaned_data.get("category")
            if account:
                monthly_queryset = monthly_queryset.filter(
                    Q(account=account) | Q(destination_account=account)
                )
            if category:
                monthly_queryset = monthly_queryset.filter(category=category)

        monthly_income = monthly_queryset.filter(
            transaction_type=Transaction.TransactionType.INCOME
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))['total']
        monthly_expense = monthly_queryset.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))['total']

        return current_balance, monthly_income - monthly_expense

    def get_filtered_transactions(self, form, selected_month):
        queryset = Transaction.objects.filter(user=self.request.user).select_related(
            "account", "destination_account", "category"
        )
        return self.apply_filters(queryset, form, selected_month, include_query=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_filter_form()
        selected_month, selected_month_value = self.get_selected_month()

        selected_month_label, prev_month_query, next_month_query = self.get_month_navigation(
            selected_month
        )
        transactions = self.get_filtered_transactions(form, selected_month)
        current_balance, monthly_balance = self.get_balances(form, selected_month)

        query_params = self.request.GET.copy()
        query_params["month"] = selected_month_value

        context["filter_form"] = form
        context["transactions"] = transactions
        context["querystring"] = query_params.urlencode()
        context["selected_month_value"] = selected_month_value
        context["selected_month_label"] = selected_month_label
        context["prev_month_query"] = prev_month_query
        context["next_month_query"] = next_month_query
        context["current_query"] = self.request.GET.get("query", "")
        context["selected_account_id"] = self.request.GET.get("account", "")
        context["selected_category_id"] = self.request.GET.get("category", "")
        context["current_balance"] = current_balance
        context["monthly_balance"] = monthly_balance
        return context


class StatementView(StatementViewBase):
    template_name = "transactions/statement.html"


class StatementPartialView(StatementViewBase):
    template_name = "transactions/partials/statement_list.html"


class QuickTransactionCreateView(LoginRequiredMixin, TransactionFormKwargsMixin, CreateView):
    model = Transaction
    form_class = QuickTransactionForm
    template_name = "transactions/partials/quick_add_modal.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        self.object.generate_future_occurrences()
        response = HttpResponse(status=204)
        response["HX-Trigger"] = json.dumps(
            {"transactionAdded": {"id": self.object.id}, "closeModal": True}
        )
        return response

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

