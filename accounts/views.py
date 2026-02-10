from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.forms import AccountForm
from accounts.models import Account
from common.mixins import UserAssignMixin, UserQuerySetMixin


class AccountListView(UserQuerySetMixin, ListView):
    model = Account
    template_name = "accounts/account_list.html"
    context_object_name = "accounts"


class AccountCreateView(UserAssignMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = "accounts/account_form.html"
    success_url = reverse_lazy("accounts:list")


class AccountUpdateView(UserQuerySetMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = "accounts/account_form.html"
    success_url = reverse_lazy("accounts:list")


class AccountDeleteView(UserQuerySetMixin, DeleteView):
    model = Account
    template_name = "accounts/account_confirm_delete.html"
    success_url = reverse_lazy("accounts:list")
