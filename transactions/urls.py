from django.urls import path

from transactions.views import (
    QuickTransactionCreateView,
    StatementPartialView,
    StatementView,
    TransactionCreateView,
    TransactionDeleteView,
    TransactionUpdateView,
)

app_name = "transactions"

urlpatterns = [
    path("", StatementView.as_view(), name="statement"),
    path("partial/", StatementPartialView.as_view(), name="statement-partial"),
    path("new/", TransactionCreateView.as_view(), name="create"),
    path("quick-add/", QuickTransactionCreateView.as_view(), name="quick-add"),
    path("<int:pk>/edit/", TransactionUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", TransactionDeleteView.as_view(), name="delete"),
]
