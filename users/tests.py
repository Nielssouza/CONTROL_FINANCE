from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class UserAuthFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="auth-user",
            password="strong-pass-123",
        )

    def test_login_page_disables_cache_and_refreshes_if_restored(self):
        response = self.client.get(reverse("users:login"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertContains(response, 'window.addEventListener("pageshow"')
        self.assertContains(response, "window.location.reload()")

    def test_logout_redirect_disables_cache(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("users:login"))
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    def test_user_can_log_in_again_after_logout(self):
        login_url = reverse("users:login")

        first_login = self.client.post(
            login_url,
            {"username": "auth-user", "password": "strong-pass-123"},
        )
        self.assertRedirects(first_login, reverse("dashboard:home"))

        logout = self.client.post(reverse("users:logout"))
        self.assertRedirects(logout, login_url)

        second_login = self.client.post(
            login_url,
            {"username": "auth-user", "password": "strong-pass-123"},
        )
        self.assertRedirects(second_login, reverse("dashboard:home"))
