"""Page views plus a small JSON API. All mutations require Django CSRF tokens."""
from functools import wraps
from urllib.parse import parse_qs, urlsplit
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from .crypto import token_digest
from .gateway import GatewayError, issue_session, revoke_session
from .models import RemoteSession, Server

class PortalLogin(LoginView):
    template_name = "portal/login.html"
    redirect_authenticated_user = True

def api_login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Please log in again."}, status=401)
        return view(request, *args, **kwargs)
    return never_cache(wrapped)

def home(request):
    return redirect("dashboard" if request.user.is_authenticated else "login")

@login_required
@never_cache
def dashboard(request):
    servers = Server.objects.filter(enabled=True)
    if not request.user.is_superuser:
        servers = servers.filter(allowed_users=request.user)
    return render(request, "portal/dashboard.html", {"servers": servers})

def permitted_server(request, server_id):
    servers = Server.objects.filter(enabled=True)
    if not request.user.is_superuser:
        servers = servers.filter(allowed_users=request.user)
    return get_object_or_404(servers, pk=server_id)

@login_required
@never_cache
def desktop(request, server_id):
    server = permitted_server(request, server_id)
    return render(request, "portal/desktop.html", {"server": server})

@require_POST
@api_login_required
def start_session(request, server_id):
    server = permitted_server(request, server_id)
    # Bound resource use for this home-lab version.
    if RemoteSession.objects.filter(user=request.user, stop_requested=False, expires_at__gt=timezone.now()).count() >= 3:
        return JsonResponse({"error": "Three sessions are already open. Disconnect one first."}, status=409)
    try:
        result = issue_session(request.user, server, request.session.session_key)
        return JsonResponse(result, status=201)
    except GatewayError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

def owned_session(request, session_id):
    return get_object_or_404(RemoteSession.objects.select_related("server"), pk=session_id,
                            user=request.user, django_session_key=request.session.session_key)

@require_POST
@api_login_required
def heartbeat(request, session_id):
    record = owned_session(request, session_id)
    if record.stop_requested or record.expires_at <= timezone.now() or not record.server.can_access(request.user):
        revoke_session(record)
        return JsonResponse({"error": "This session has ended or permission was removed."}, status=403)
    RemoteSession.objects.filter(pk=record.pk).update(last_seen=timezone.now())
    return JsonResponse({"ok": True})

@require_POST
@api_login_required
def stop_session(request, session_id):
    record = owned_session(request, session_id)
    complete = revoke_session(record)
    return JsonResponse({"closed": complete, "cleanup_pending": not complete}, status=200 if complete else 202)

@require_POST
@login_required
def logout_view(request):
    # Close this browser login's sessions; do not disrupt a different login/device.
    for record in RemoteSession.objects.filter(user=request.user, django_session_key=request.session.session_key, revoked_at=None):
        revoke_session(record)
    logout(request)
    return redirect("login")

@require_GET
def gateway_check(request):
    """Called only by nginx's internal auth_request before a tunnel opens."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    # Check WebSocket Origin too: Django CSRF middleware does not cover upgrades.
    if request.headers.get("Origin") != settings.PUBLIC_ORIGIN:
        return HttpResponse(status=403)
    query = parse_qs(urlsplit(request.headers.get("X-Original-URI", "")).query)
    token = query.get("token", [""])[0]
    if not token:
        return HttpResponse(status=403)
    record = RemoteSession.objects.select_related("server").filter(token_hash=token_digest(token),
        user=request.user, django_session_key=request.session.session_key,
        stop_requested=False, expires_at__gt=timezone.now()).first()
    if not record or not record.server.can_access(request.user):
        return HttpResponse(status=403)
    return HttpResponse(status=204)

@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
