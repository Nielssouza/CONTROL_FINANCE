from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from shopping.models import ShoppingItem


class ShoppingViewsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="shopping-user", password="pass-12345")
        self.other_user = user_model.objects.create_user(
            username="shopping-other", password="pass-12345"
        )

        self.item = ShoppingItem.objects.create(
            user=self.user,
            title="Cafe",
            quantity=2,
            unit_price=Decimal("12.50"),
            is_purchased=False,
        )
        ShoppingItem.objects.create(
            user=self.other_user,
            title="Azeite",
            quantity=1,
            unit_price=Decimal("20.00"),
            is_purchased=False,
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("shopping:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response["Location"])

    def test_list_shows_only_current_user_items(self):
        self.client.login(username="shopping-user", password="pass-12345")
        response = self.client.get(reverse("shopping:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cafe")
        self.assertNotContains(response, "Azeite")

    def test_summary_estimate_counts_only_purchased_items(self):
        ShoppingItem.objects.create(
            user=self.user,
            title="Arroz",
            quantity=3,
            unit_price=Decimal("10.00"),
            is_purchased=True,
        )
        ShoppingItem.objects.create(
            user=self.user,
            title="Leite",
            quantity=2,
            unit_price=Decimal("5.00"),
            is_purchased=False,
        )

        self.client.login(username="shopping-user", password="pass-12345")
        response = self.client.get(reverse("shopping:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["purchased_total"], Decimal("30.00"))

    def test_toggle_purchased_changes_status(self):
        self.client.login(username="shopping-user", password="pass-12345")

        response = self.client.post(
            reverse("shopping:toggle-purchased", args=[self.item.pk]),
            data={"next": "/shopping/"},
        )

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_purchased)
        self.assertIsNotNone(self.item.purchased_at)

    def test_toggle_purchased_with_htmx_returns_redirect(self):
        self.client.login(username="shopping-user", password="pass-12345")

        response = self.client.post(
            reverse("shopping:toggle-purchased", args=[self.item.pk]),
            data={"next": "/shopping/"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers.get("HX-Redirect"), "/shopping/")
