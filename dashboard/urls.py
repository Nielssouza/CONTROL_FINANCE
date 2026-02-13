from django.urls import path

from dashboard.views import (
    DashboardChartsView,
    DashboardHomeView,
    DashboardLatestPartialView,
    DashboardSummaryPartialView,
)

app_name = "dashboard"

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="home"),
    path("dashboard/charts/", DashboardChartsView.as_view(), name="charts"),
    path("dashboard/summary/", DashboardSummaryPartialView.as_view(), name="summary"),
    path("dashboard/latest/", DashboardLatestPartialView.as_view(), name="latest"),
]
