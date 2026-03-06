from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from common.mixins import UserAssignMixin, UserQuerySetMixin
from shopping.forms import ShoppingItemForm
from shopping.models import ShoppingItem


class ShoppingListView(UserQuerySetMixin, ListView):
    model = ShoppingItem
    template_name = "shopping/shopping_list.html"
    context_object_name = "items"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.object_list
        pending_qs = queryset.filter(is_purchased=False)
        purchased_qs = queryset.filter(is_purchased=True)

        total_expr = ExpressionWrapper(
            Coalesce(F("unit_price"), Value(Decimal("0.00"))) * F("quantity"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )

        purchased_total = purchased_qs.aggregate(
            total=Coalesce(Sum(total_expr), Decimal("0.00"))
        )["total"]

        context.update(
            {
                "pending_count": pending_qs.count(),
                "purchased_count": purchased_qs.count(),
                "purchased_total": purchased_total,
            }
        )
        return context


class ShoppingItemCreateView(UserAssignMixin, CreateView):
    model = ShoppingItem
    form_class = ShoppingItemForm
    template_name = "shopping/shopping_form.html"
    success_url = reverse_lazy("shopping:list")


class ShoppingItemUpdateView(UserQuerySetMixin, UpdateView):
    model = ShoppingItem
    form_class = ShoppingItemForm
    template_name = "shopping/shopping_form.html"
    success_url = reverse_lazy("shopping:list")


class ShoppingItemDeleteView(UserQuerySetMixin, DeleteView):
    model = ShoppingItem
    template_name = "shopping/shopping_confirm_delete.html"
    success_url = reverse_lazy("shopping:list")


class ShoppingItemTogglePurchasedView(LoginRequiredMixin, View):
    success_url = reverse_lazy("shopping:list")

    def post(self, request, *args, **kwargs):
        item = get_object_or_404(ShoppingItem, pk=kwargs.get("pk"), user=request.user)
        item.toggle_purchased()
        item.save(update_fields=["is_purchased", "purchased_at", "updated_at"])

        next_url = (request.POST.get("next") or "").strip()
        if not next_url.startswith("/"):
            next_url = str(self.success_url)

        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=204)
            response["HX-Redirect"] = next_url
            return response

        return HttpResponseRedirect(next_url)
