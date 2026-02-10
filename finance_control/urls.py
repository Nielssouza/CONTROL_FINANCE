from django.contrib import admin
from django.urls import include, path

from finance_control.views import ManifestView, ServiceWorkerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("manifest.json", ManifestView.as_view(), name="manifest"),
    path("service-worker.js", ServiceWorkerView.as_view(), name="service-worker"),
    path("users/", include("users.urls")),
    path("accounts/", include("accounts.urls")),
    path("categories/", include("categories.urls")),
    path("transactions/", include("transactions.urls")),
    path("goals/", include("goals.urls")),
    path("", include("dashboard.urls")),
]
