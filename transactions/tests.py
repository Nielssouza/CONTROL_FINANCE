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
            "recurrence_interval_unit": Transaction.IntervalUnit.MONTH,
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
            "recurrence_interval_unit": Transaction.IntervalUnit.MONTH,
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

    def test_update_closed_month_allows_change_without_password(self):
        self._close_month(2026, 2)
        payload = self._build_edit_payload(description="Novo texto", scope="current")

        response = self.client.post(
            reverse("transactions:update", args=[self.feb.pk]),
            data=payload,
        )

        self.assertEqual(response.status_code, 302)
        self.feb.refresh_from_db()
        self.assertEqual(self.feb.description, "Novo texto")

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

    def test_delete_closed_month_allows_deletion_without_password(self):
        self._close_month(2026, 2)

        response = self.client.post(
            reverse("transactions:delete", args=[self.feb.pk]),
            data={"scope": "current", "unlock_password": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Transaction.objects.filter(pk=self.feb.pk).exists())

    def test_delete_cleared_transaction_is_blocked(self):
        self.feb.is_cleared = True
        self.feb.save(update_fields=["is_cleared"])

        response = self.client.post(
            reverse("transactions:delete", args=[self.feb.pk]),
            data={"scope": "current", "unlock_password": "scope-pass-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Transaction.objects.filter(pk=self.feb.pk).exists())

    def test_create_closed_month_allows_creation_without_password(self):
        self._close_month(2026, 2)

        response = self.client.post(
            reverse("transactions:create"),
            data=self._build_create_payload(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Transaction.objects.filter(
                user=self.user,
                date=date(2026, 2, 5),
                description="Extra",
            ).exists()
        )


    def test_pending_expense_uses_cleared_style_only_when_baixada(self):
        expense_category = Category.objects.create(
            user=self.user,
            name="Aluguel",
            category_type=Category.CategoryType.EXPENSE,
        )

        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("50.00"),
            date=date(2026, 2, 15),
            account=self.account,
            category=expense_category,
            description="Despesa pendente",
            is_cleared=False,
            recurrence_type=Transaction.RecurrenceType.ONCE,
        )

        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("70.00"),
            date=date(2026, 2, 16),
            account=self.account,
            category=expense_category,
            description="Despesa baixada",
            is_cleared=True,
            recurrence_type=Transaction.RecurrenceType.ONCE,
        )

        response = self.client.get(
            reverse("transactions:statement"),
            {"month": "2026-02"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="txn-amount txn-amount-expense">R$ 50,00</p>', html=False)
        self.assertContains(response, 'class="txn-amount txn-amount-expense txn-amount-cleared">R$ 70,00</p>', html=False)

    def test_generate_future_occurrences_respects_day_unit(self):
        tx = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("10.00"),
            date=date(2026, 2, 1),
            account=self.account,
            category=self.category,
            description="Fixa em dias",
            recurrence_type=Transaction.RecurrenceType.FIXED,
            recurrence_interval=10,
            recurrence_interval_unit=Transaction.IntervalUnit.DAY,
            is_cleared=False,
        )

        created_count = tx.generate_future_occurrences()

        self.assertGreater(created_count, 0)
        self.assertTrue(
            Transaction.objects.filter(
                user=self.user,
                description="Fixa em dias",
                date=date(2026, 2, 11),
            ).exists()
        )


    def test_installment_transactions_get_sequential_numbers(self):
        expense_category = Category.objects.create(
            user=self.user,
            name="Curso",
            category_type=Category.CategoryType.EXPENSE,
        )
        tx = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("100.00"),
            date=date(2026, 2, 20),
            account=self.account,
            category=expense_category,
            description="Curso online",
            recurrence_type=Transaction.RecurrenceType.INSTALLMENT,
            recurrence_interval_unit=Transaction.IntervalUnit.MONTH,
            installment_count=3,
            is_cleared=False,
        )

        created_count = tx.generate_future_occurrences()

        self.assertEqual(created_count, 2)
        installments = list(
            Transaction.objects.filter(
                user=self.user,
                description="Curso online",
            ).order_by("date")
        )
        self.assertEqual([item.installment_number for item in installments], [1, 2, 3])

    def test_statement_shows_installment_fraction_in_title(self):
        expense_category = Category.objects.create(
            user=self.user,
            name="Parcelado",
            category_type=Category.CategoryType.EXPENSE,
        )
        tx = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("150.00"),
            date=date(2026, 2, 21),
            account=self.account,
            category=expense_category,
            description="Notebook",
            recurrence_type=Transaction.RecurrenceType.INSTALLMENT,
            recurrence_interval_unit=Transaction.IntervalUnit.MONTH,
            installment_count=3,
            is_cleared=False,
        )
        tx.generate_future_occurrences()

        feb_response = self.client.get(reverse("transactions:statement"), {"month": "2026-02"})
        mar_response = self.client.get(reverse("transactions:statement"), {"month": "2026-03"})

        self.assertEqual(feb_response.status_code, 200)
        self.assertEqual(mar_response.status_code, 200)
        self.assertContains(feb_response, "Notebook (1/3)")
        self.assertContains(mar_response, "Notebook (2/3)")

    def test_toggle_ignored_expense_excludes_from_monthly_balance(self):
        expense_category = Category.objects.create(
            user=self.user,
            name="Internet",
            category_type=Category.CategoryType.EXPENSE,
        )
        expense = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("500.00"),
            date=date(2026, 2, 12),
            account=self.account,
            category=expense_category,
            description="Internet",
            is_cleared=False,
            recurrence_type=Transaction.RecurrenceType.ONCE,
        )

        before_response = self.client.get(reverse("transactions:statement"), {"month": "2026-02"})
        self.assertEqual(before_response.status_code, 200)
        self.assertEqual(before_response.context["monthly_balance"], Decimal("6500.00"))

        toggle_response = self.client.post(
            reverse("transactions:toggle-ignored", args=[expense.pk]),
            data={"next": "/transactions/?month=2026-02"},
        )
        self.assertEqual(toggle_response.status_code, 302)

        expense.refresh_from_db()
        self.assertTrue(expense.is_ignored)

        after_response = self.client.get(reverse("transactions:statement"), {"month": "2026-02"})
        self.assertEqual(after_response.status_code, 200)
        self.assertEqual(after_response.context["monthly_balance"], Decimal("7000.00"))

    def test_toggle_cleared_removes_ignored_flag_and_sets_baixada(self):
        expense_category = Category.objects.create(
            user=self.user,
            name="Condominio",
            category_type=Category.CategoryType.EXPENSE,
        )
        expense = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("200.00"),
            date=date(2026, 2, 18),
            account=self.account,
            category=expense_category,
            description="Condominio",
            is_cleared=False,
            is_ignored=True,
            recurrence_type=Transaction.RecurrenceType.ONCE,
        )

        response = self.client.post(
            reverse("transactions:toggle-cleared", args=[expense.pk]),
            data={"next": "/transactions/?month=2026-02"},
        )
        self.assertEqual(response.status_code, 302)

        expense.refresh_from_db()
        self.assertTrue(expense.is_cleared)
        self.assertFalse(expense.is_ignored)



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
