from django.urls import path

from shopping.views import (
    ShoppingItemCreateView,
    ShoppingItemDeleteView,
    ShoppingItemTogglePurchasedView,
    ShoppingItemUpdateView,
    ShoppingListView,
)

app_name = "shopping"

urlpatterns = [
    path("", ShoppingListView.as_view(), name="list"),
    path("new/", ShoppingItemCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", ShoppingItemUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", ShoppingItemDeleteView.as_view(), name="delete"),
    path("<int:pk>/toggle-purchased/", ShoppingItemTogglePurchasedView.as_view(), name="toggle-purchased"),
]
