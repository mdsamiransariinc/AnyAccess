from django.contrib import admin
from django.urls import path
from portal import views
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home),
    path("login/", views.PortalLogin.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("servers/<int:server_id>/", views.desktop, name="desktop"),
    path("api/servers/<int:server_id>/sessions/", views.start_session, name="start-session"),
    path("api/sessions/<uuid:session_id>/heartbeat/", views.heartbeat),
    path("api/sessions/<uuid:session_id>/stop/", views.stop_session),
    path("api/gateway-check/", views.gateway_check),
    path("health/", views.health),
]
