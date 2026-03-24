from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.forms import StyledAuthenticationForm


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
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, "navigator.credentials.preventSilentAccess")
        self.assertContains(response, 'new URLSearchParams(window.location.search).has("logged_out")')

    def test_logout_redirect_disables_cache(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, 302)
        redirect_url = response.headers["Location"]
        parsed = urlparse(redirect_url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, reverse("users:login"))
        self.assertIn("logged_out", query)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertEqual(response.headers.get("Clear-Site-Data"), '"cache"')
        self.assertIn("sessionid", response.cookies)
        self.assertIn("csrftoken", response.cookies)
        self.assertEqual(response.cookies["sessionid"].value, "")
        self.assertEqual(response.cookies["csrftoken"].value, "")

    def test_user_can_log_in_again_after_logout(self):
        login_url = reverse("users:login")

        first_login = self.client.post(
            login_url,
            {"username": "auth-user", "password": "strong-pass-123"},
        )
        self.assertRedirects(first_login, reverse("dashboard:home"))

        logout = self.client.post(reverse("users:logout"))
        logout_redirect = urlparse(logout.headers["Location"])
        self.assertEqual(logout.status_code, 302)
        self.assertEqual(logout_redirect.path, login_url)

        second_login = self.client.post(
            login_url,
            {"username": "auth-user", "password": "strong-pass-123"},
        )
        self.assertRedirects(second_login, reverse("dashboard:home"))

    def test_auth_form_preserves_mobile_friendly_login_attributes(self):
        form = StyledAuthenticationForm()

        self.assertEqual(form.fields["username"].widget.attrs.get("autocomplete"), "username")
        self.assertEqual(form.fields["username"].widget.attrs.get("autocapitalize"), "none")
        self.assertEqual(form.fields["username"].widget.attrs.get("autocorrect"), "off")
        self.assertEqual(form.fields["password"].widget.attrs.get("autocomplete"), "current-password")
        self.assertEqual(form.fields["password"].widget.attrs.get("autocapitalize"), "none")
        self.assertFalse(form.fields["password"].strip)
