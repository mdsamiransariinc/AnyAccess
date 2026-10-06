"""Background cleanup for closed tabs, revoked permissions, and expired logins."""
import time
from datetime import timedelta
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone
from portal.gateway import revoke_session
from portal.models import RemoteSession

class Command(BaseCommand):
    help = "Revoke stale remote sessions; use --loop in the cleanup container."
    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")
    def handle(self, *args, **options):
        while True:
            close_old_connections()
            now = timezone.now()
            for record in RemoteSession.objects.filter(revoked_at=None).select_related("server", "user"):
                login_exists = Session.objects.filter(session_key=record.django_session_key, expire_date__gt=now).exists()
                stale = record.last_seen < now - timedelta(seconds=settings.REMOTE_HEARTBEAT_GRACE)
                if record.stop_requested or stale or record.expires_at <= now or not login_exists or not record.server.can_access(record.user):
                    revoke_session(record)
            if not options["loop"]:
                break
            time.sleep(20)
