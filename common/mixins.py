from django.contrib.auth.mixins import LoginRequiredMixin


class UserQuerySetMixin(LoginRequiredMixin):
    owner_field = "user"
    tenant_field = "tenant"

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(queryset.model, self.tenant_field) and getattr(self.request, "tenant", None):
            return queryset.filter(**{self.tenant_field: self.request.tenant})
        return queryset.filter(**{self.owner_field: self.request.user})


class UserAssignMixin(LoginRequiredMixin):
    owner_field = "user"
    tenant_field = "tenant"

    def form_valid(self, form):
        if hasattr(form.instance, self.owner_field):
            setattr(form.instance, self.owner_field, self.request.user)
        if hasattr(form.instance, self.tenant_field) and getattr(self.request, "tenant", None):
            setattr(form.instance, self.tenant_field, self.request.tenant)
        return super().form_valid(form)
