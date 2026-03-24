from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from common.mixins import UserAssignMixin, UserQuerySetMixin
from goals.forms import GoalEntryForm, GoalForm
from goals.models import SavingGoal


class GoalListView(UserQuerySetMixin, ListView):
    model = SavingGoal
    template_name = "goals/goal_list.html"
    context_object_name = "goals"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("entries")


class GoalCreateView(UserAssignMixin, CreateView):
    model = SavingGoal
    form_class = GoalForm
    template_name = "goals/goal_form.html"
    success_url = reverse_lazy("goals:list")

    def form_valid(self, form):
        messages.success(self.request, "Objetivo criado com sucesso.")
        return super().form_valid(form)


class GoalUpdateView(UserQuerySetMixin, UpdateView):
    model = SavingGoal
    form_class = GoalForm
    template_name = "goals/goal_form.html"

    def get_success_url(self):
        messages.success(self.request, "Objetivo atualizado com sucesso.")
        return reverse_lazy("goals:detail", kwargs={"pk": self.object.pk})


class GoalDetailView(UserQuerySetMixin, DetailView):
    model = SavingGoal
    template_name = "goals/goal_detail.html"
    context_object_name = "goal"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        goal = self.object
        context["entries"] = goal.entries.all()[:30]
        context["entry_form"] = kwargs.get("entry_form") or GoalEntryForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = GoalEntryForm(request.POST)
        form.instance.goal = self.object
        form.instance.user = request.user

        if form.is_valid():
            form.instance.tenant = request.tenant
            form.save()
            messages.success(request, "Lancamento registrado no objetivo.")
            return redirect("goals:detail", pk=self.object.pk)

        context = self.get_context_data(entry_form=form)
        return self.render_to_response(context, status=400)

