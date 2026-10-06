from django import forms
from django.contrib import admin
from .crypto import encrypt_secret
from .models import Server, RemoteSession

class ServerForm(forms.ModelForm):
    remote_password = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False),
        help_text="Enter a password to set/replace it. Leave blank to preserve the saved password.")
    clear_password = forms.BooleanField(required=False, help_text="Explicitly erase the saved password.")
    class Meta:
        model = Server
        fields = "__all__"
    def clean(self):
        values = super().clean()
        host = values.get("hostname", "")
        if any(c in host for c in ["/", "@", " ", "\\"]):
            self.add_error("hostname", "Use an IP address or DNS name, not a URL.")
        if values.get("clear_password") and values.get("remote_password"):
            raise forms.ValidationError("Either set a password or clear it, not both.")
        return values
    def save(self, commit=True):
        server = super().save(commit=False)
        if self.cleaned_data.get("clear_password"):
            server.password_encrypted = ""
        elif self.cleaned_data.get("remote_password"):
            server.password_encrypted = encrypt_secret(self.cleaned_data["remote_password"])
        if commit:
            server.save()
            self.save_m2m()
        return server

@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    form = ServerForm
    list_display = ("name", "operating_system", "protocol", "hostname", "enabled")
    filter_horizontal = ("allowed_users",)
    list_filter = ("enabled", "operating_system")

@admin.register(RemoteSession)
class RemoteSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "server", "created_at", "stop_requested", "revoked_at")
    fields = ("id", "user", "server", "created_at", "last_seen", "expires_at", "stop_requested", "revoked_at")
    readonly_fields = fields
    actions = ["disconnect_selected"]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    @admin.action(description="Disconnect selected sessions")
    def disconnect_selected(self, request, queryset):
        from .gateway import revoke_session
        for session in queryset:
            revoke_session(session)
