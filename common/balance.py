from decimal import Decimal

from django.apps import apps
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from transactions.models import Transaction


ZERO = Decimal("0.00")


def _sum_amount(queryset):
    return queryset.aggregate(total=Coalesce(Sum("amount"), ZERO))["total"]


def tracked_accounts(queryset):
    return queryset.filter(include_in_balance=True)


def calculate_account_balance(account, cutoff_date=None):
    if not account.include_in_balance:
        return ZERO

    cutoff_date = cutoff_date or timezone.localdate()

    posted_transactions = account.transactions.filter(
        is_cleared=True,
        is_ignored=False,
        date__lte=cutoff_date,
    )
    incoming_transfers = account.incoming_transfers.filter(
        transaction_type=Transaction.TransactionType.TRANSFER,
        is_cleared=True,
        is_ignored=False,
        date__lte=cutoff_date,
    )

    income = _sum_amount(
        posted_transactions.filter(transaction_type=Transaction.TransactionType.INCOME)
    )
    expense = _sum_amount(
        posted_transactions.filter(transaction_type=Transaction.TransactionType.EXPENSE)
    )
    outgoing_transfers = _sum_amount(
        posted_transactions.filter(transaction_type=Transaction.TransactionType.TRANSFER)
    )
    incoming_total = _sum_amount(incoming_transfers)

    return (
        account.initial_balance
        + income
        + incoming_total
        - expense
        - outgoing_transfers
    )


def calculate_user_balance(user, cutoff_date):
    account_model = apps.get_model("accounts", "Account")
    posted_transactions = Transaction.objects.filter(
        user=user,
        is_cleared=True,
        is_ignored=False,
        date__lte=cutoff_date,
    )

    initial_total = tracked_accounts(
        account_model.objects.filter(user=user, is_active=True)
    ).aggregate(total=Coalesce(Sum("initial_balance"), ZERO))["total"]

    total_income = _sum_amount(
        posted_transactions.filter(
            transaction_type=Transaction.TransactionType.INCOME
        ).filter(account__include_in_balance=True)
    )
    total_expense = _sum_amount(
        posted_transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        ).filter(account__include_in_balance=True)
    )
    total_outgoing_transfers = _sum_amount(
        posted_transactions.filter(
            transaction_type=Transaction.TransactionType.TRANSFER
        ).filter(account__include_in_balance=True)
    )
    total_incoming_transfers = _sum_amount(
        posted_transactions.filter(
            transaction_type=Transaction.TransactionType.TRANSFER
        ).filter(destination_account__include_in_balance=True)
    )

    return (
        initial_total
        + total_income
        + total_incoming_transfers
        - total_expense
        - total_outgoing_transfers
    )


def calculate_monthly_balance(user, selected_month, account=None, category=None):
    monthly_transactions = Transaction.objects.filter(
        user=user,
        is_ignored=False,
        date__year=selected_month.year,
        date__month=selected_month.month,
    )

    if category:
        monthly_transactions = monthly_transactions.filter(category=category)

    if account:
        if not account.include_in_balance:
            return ZERO

        income = _sum_amount(
            monthly_transactions.filter(
                transaction_type=Transaction.TransactionType.INCOME,
                account=account,
            )
        )
        expense = _sum_amount(
            monthly_transactions.filter(
                transaction_type=Transaction.TransactionType.EXPENSE,
                account=account,
            )
        )
        outgoing_transfers = _sum_amount(
            monthly_transactions.filter(
                transaction_type=Transaction.TransactionType.TRANSFER,
                account=account,
            )
        )
        incoming_transfers = _sum_amount(
            monthly_transactions.filter(
                transaction_type=Transaction.TransactionType.TRANSFER,
                destination_account=account,
            )
        )

        return income + incoming_transfers - expense - outgoing_transfers

    income = _sum_amount(
        monthly_transactions.filter(
            transaction_type=Transaction.TransactionType.INCOME
        ).filter(account__include_in_balance=True)
    )
    expense = _sum_amount(
        monthly_transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        ).filter(account__include_in_balance=True)
    )
    outgoing_transfers = _sum_amount(
        monthly_transactions.filter(
            transaction_type=Transaction.TransactionType.TRANSFER
        ).filter(account__include_in_balance=True)
    )
    incoming_transfers = _sum_amount(
        monthly_transactions.filter(
            transaction_type=Transaction.TransactionType.TRANSFER
        ).filter(destination_account__include_in_balance=True)
    )

    return income + incoming_transfers - expense - outgoing_transfers
