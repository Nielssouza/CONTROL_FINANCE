from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Account
from categories.models import Category
from transactions.models import ClosedMonth, Transaction


class TransactionScopeAndMonthLockTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="scope-user",
            password="scope-pass-123",
        )
        self.client.login(username="scope-user", password="scope-pass-123")

        self.account = Account.objects.create(
            user=self.user,
            name="Banco",
            account_type=Account.AccountType.BANK,
            initial_balance=Decimal("0.00"),
            is_active=True,
        )
        self.category = Category.objects.create(
            user=self.user,
            name="Salario",
            category_type=Category.CategoryType.INCOME,
        )

        self.jan = self._create_tx(date(2026, 1, 10))
        self.feb = self._create_tx(date(2026, 2, 10))
        self.mar = self._create_tx(date(2026, 3, 10))

    def _create_tx(self, tx_date):
        return Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("7000.00"),
            date=tx_date,
            account=self.account,
            category=self.category,
            description="Salarios",
            is_cleared=False,
            recurrence_type=Transaction.RecurrenceType.FIXED,
            recurrence_interval=1,
        )

    def _close_month(self, year, month):
        ClosedMonth.objects.create(user=self.user, year=year, month=month, is_closed=True)

    def _build_edit_payload(self, **overrides):
        data = {
            "transaction_type": Transaction.TransactionType.INCOME,
            "amount": "R$ 7.000,00",
            "date": self.feb.date.isoformat(),
            "is_cleared": "",
            "account": str(self.account.pk),
            "destination_account": "",
            "category": str(self.category.pk),
            "description": "Salarios",
            "recurrence_type": Transaction.RecurrenceType.FIXED,
            "installment_count": "",
            "recurrence_interval": "1",
            "unlock_password": "",
        }
        data.update(overrides)
        return data

    def _build_create_payload(self, **overrides):
        data = {
            "transaction_type": Transaction.TransactionType.INCOME,
            "amount": "R$ 1.000,00",
            "date": "2026-02-05",
            "is_cleared": "",
            "account": str(self.account.pk),
            "destination_account": "",
            "category": str(self.category.pk),
            "description": "Extra",
            "recurrence_type": Transaction.RecurrenceType.FIXED,
            "installment_count": "",
            "recurrence_interval": "1",
            "unlock_password": "",
        }
        data.update(overrides)
        return data

    def test_update_scope_current_changes_only_selected_transaction(self):
        payload = self._build_edit_payload(amount="R$ 7.200,00", scope="current")

        response = self.client.post(
            reverse("transactions:update", args=[self.feb.pk]),
            data=payload,
        )

        self.assertEqual(response.status_code, 302)
        self.jan.refresh_from_db()
        self.feb.refresh_from_db()
        self.mar.refresh_from_db()

        self.assertEqual(self.jan.amount, Decimal("7000.00"))
        self.assertEqual(self.feb.amount, Decimal("7200.00"))
        self.assertEqual(self.mar.amount, Decimal("7000.00"))

    def test_update_scope_all_changes_all_pending_transactions_in_series(self):
        self.jan.is_cleared = True
        self.jan.save(update_fields=["is_cleared"])

        payload = self._build_edit_payload(description="Salario principal", scope="all")

        response = self.client.post(
            reverse("transactions:update", args=[self.feb.pk]),
            data=payload,
        )

        self.assertEqual(response.status_code, 302)
        self.jan.refresh_from_db()
        self.feb.refresh_from_db()
        self.mar.refresh_from_db()

        self.assertEqual(self.jan.description, "Salarios")  # baixada nao muda
        self.assertEqual(self.feb.description, "Salario principal")
        self.assertEqual(self.mar.description, "Salario principal")

    def test_update_closed_month_requires_password(self):
        self._close_month(2026, 2)
        payload = self._build_edit_payload(description="Novo texto", scope="current")

        response = self.client.post(
            reverse("transactions:update", args=[self.feb.pk]),
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        self.feb.refresh_from_db()
        self.assertEqual(self.feb.description, "Salarios")

    def test_update_closed_month_with_password_allows_change(self):
        self._close_month(2026, 2)
        payload = self._build_edit_payload(
            description="Novo texto",
            scope="current",
            unlock_password="scope-pass-123",
        )

        response = self.client.post(
            reverse("transactions:update", args=[self.feb.pk]),
            data=payload,
        )

        self.assertEqual(response.status_code, 302)
        self.feb.refresh_from_db()
        self.assertEqual(self.feb.description, "Novo texto")

    def test_delete_scope_current_removes_only_selected_transaction(self):
        response = self.client.post(
            reverse("transactions:delete", args=[self.feb.pk]),
            data={"scope": "current", "unlock_password": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Transaction.objects.filter(pk=self.jan.pk).exists())
        self.assertFalse(Transaction.objects.filter(pk=self.feb.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=self.mar.pk).exists())

    def test_delete_scope_all_removes_all_pending_transactions_in_series(self):
        self.jan.is_cleared = True
        self.jan.save(update_fields=['is_cleared'])
        response = self.client.post(
            reverse("transactions:delete", args=[self.feb.pk]),
            data={"scope": "all", "unlock_password": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Transaction.objects.filter(pk=self.jan.pk).exists())  # baixada permanece
        self.assertFalse(Transaction.objects.filter(pk=self.feb.pk).exists())
        self.assertFalse(Transaction.objects.filter(pk=self.mar.pk).exists())

    def test_delete_closed_month_requires_password(self):
        self._close_month(2026, 2)

        response = self.client.post(
            reverse("transactions:delete", args=[self.feb.pk]),
            data={"scope": "current", "unlock_password": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Transaction.objects.filter(pk=self.feb.pk).exists())

    def test_delete_cleared_transaction_is_blocked(self):
        self.feb.is_cleared = True
        self.feb.save(update_fields=["is_cleared"])

        response = self.client.post(
            reverse("transactions:delete", args=[self.feb.pk]),
            data={"scope": "current", "unlock_password": "scope-pass-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Transaction.objects.filter(pk=self.feb.pk).exists())

    def test_create_closed_month_requires_password(self):
        self._close_month(2026, 2)

        response = self.client.post(
            reverse("transactions:create"),
            data=self._build_create_payload(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Transaction.objects.filter(
                user=self.user,
                date=date(2026, 2, 5),
                description="Extra",
            ).exists()
        )

    def test_create_closed_month_with_password_allows_creation(self):
        self._close_month(2026, 2)

        response = self.client.post(
            reverse("transactions:create"),
            data=self._build_create_payload(unlock_password="scope-pass-123"),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Transaction.objects.filter(
                user=self.user,
                date=date(2026, 2, 5),
                description="Extra",
            ).exists()
        )
