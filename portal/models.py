"""The admin manages servers; the browser never receives their saved passwords."""
import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

class Server(models.Model):
    name = models.CharField(max_length=100)
    operating_system = models.CharField(max_length=20, choices=[("windows", "Windows"), ("ubuntu", "Ubuntu"), ("linux", "Linux")])
    description = models.CharField(max_length=200, blank=True)
    protocol = models.CharField(max_length=3, choices=[("rdp", "RDP desktop"), ("vnc", "VNC desktop"), ("ssh", "SSH terminal")], default="rdp")
    hostname = models.CharField(max_length=253, help_text="VM IP/DNS reachable FROM guacd, not the browser. No URL prefix.")
    port = models.PositiveIntegerField(default=3389, validators=[MinValueValidator(1), MaxValueValidator(65535)])
    username = models.CharField(max_length=150, blank=True)
    domain = models.CharField(max_length=150, blank=True, help_text="RDP only; usually blank for local Windows accounts.")
    password_encrypted = models.TextField(blank=True, editable=False)
    ignore_certificate = models.BooleanField(default=False, help_text="RDP: enable only for your known lab VM with a self-signed certificate.")
    rdp_security = models.CharField(max_length=10, default="nla", choices=[("nla", "NLA (Windows)"), ("tls", "TLS (e.g. xrdp)"), ("any", "Negotiate")])
    enabled = models.BooleanField(default=True)
    allowed_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="assigned_servers")
    class Meta:
        ordering = ["name"]
    def __str__(self):
        return self.name
    def can_access(self, user):
        return bool(user.is_authenticated and user.is_active and self.enabled and
                    (user.is_superuser or self.allowed_users.filter(pk=user.pk).exists()))

class RemoteSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    server = models.ForeignKey(Server, on_delete=models.PROTECT)
    django_session_key = models.CharField(max_length=40)
    token_encrypted = models.TextField()
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField()
    expires_at = models.DateTimeField()
    stop_requested = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ["-created_at"]
