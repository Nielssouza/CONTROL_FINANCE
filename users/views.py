from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView
from uuid import uuid4

from users.forms import RegisterForm, StyledAuthenticationForm


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("users:login")

    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, "PUBLIC_SIGNUP_ENABLED", False):
            messages.error(request, "Cadastro publico desabilitado no momento.")
            return redirect("users:login")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.is_active = False
        self.object.save()
        messages.success(
            self.request,
            "Cadastro enviado com sucesso. Aguarde a validacao do administrador para acessar.",
        )
        return redirect(self.get_success_url())


class UserLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        self.request.session["show_post_login_loader"] = True
        return super().form_valid(form)


class UserLogoutView(LogoutView):
    def get_success_url(self):
        return f"{reverse('users:login')}?logged_out={uuid4().hex}"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response["Cache-Control"] = "max-age=0, no-cache, no-store, must-revalidate, private"
        response["Clear-Site-Data"] = '"cache"'
        response.delete_cookie(
            settings.CSRF_COOKIE_NAME,
            path=settings.CSRF_COOKIE_PATH,
            domain=settings.CSRF_COOKIE_DOMAIN,
            samesite=settings.CSRF_COOKIE_SAMESITE,
        )
        response.delete_cookie(
            settings.SESSION_COOKIE_NAME,
            path=settings.SESSION_COOKIE_PATH,
            domain=settings.SESSION_COOKIE_DOMAIN,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )
        return response
