from django.contrib.auth.mixins import LoginRequiredMixin


class UserQuerySetMixin(LoginRequiredMixin):
    owner_field = "user"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{self.owner_field: self.request.user})


class UserAssignMixin(LoginRequiredMixin):
    owner_field = "user"

    def form_valid(self, form):
        setattr(form.instance, self.owner_field, self.request.user)
        return super().form_valid(form)
