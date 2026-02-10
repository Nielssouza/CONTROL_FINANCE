from django.urls import path

from dashboard.views import (
    DashboardHomeView,
    DashboardLatestPartialView,
    DashboardSummaryPartialView,
)

app_name = "dashboard"

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="home"),
    path("dashboard/summary/", DashboardSummaryPartialView.as_view(), name="summary"),
    path("dashboard/latest/", DashboardLatestPartialView.as_view(), name="latest"),
]
