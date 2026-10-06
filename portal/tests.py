"""Focused integration checks for authentication and remote-session boundaries.

The HTTP gateway calls are mocked: these tests do NOT prove real RDP connectivity.
See docs/TESTING.md for the required live gateway + VM acceptance check.
"""
import base64
import hashlib
import hmac
import json
import subprocess
from datetime import timedelta
from unittest.mock import patch, Mock
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone
from .admin import ServerForm
from .crypto import encrypt_secret, decrypt_secret, guacamole_payload, token_digest
from .models import Server, RemoteSession

class PortalIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('alice', password='Testing-password-123')
        cls.bob = User.objects.create_user('bob', password='Testing-password-123')
        cls.server = Server.objects.create(name='Windows Lab', operating_system='windows', hostname='192.168.1.101',
            username='labuser', password_encrypted=encrypt_secret('VM-password'))
        cls.server.allowed_users.add(cls.alice)

    def setUp(self):
        self.client.force_login(self.alice)

    def record(self, **overrides):
        values = dict(user=self.alice, server=self.server,
            django_session_key=self.client.session.session_key,
            token_encrypted=encrypt_secret('test-gateway-token'), token_hash=token_digest('test-gateway-token'),
            last_seen=timezone.now(), expires_at=timezone.now() + timedelta(hours=1))
        values.update(overrides)
        return RemoteSession.objects.create(**values)

    def test_real_login_and_failed_login(self):
        client = Client()
        self.assertFalse(client.login(username='alice', password='wrong'))
        response = client.post('/login/', {'username':'alice', 'password':'Testing-password-123'})
        self.assertRedirects(response, '/dashboard/')

    def test_dashboard_and_desktop_render_without_credentials(self):
        for url in ['/dashboard/', f'/servers/{self.server.pk}/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Windows Lab')
            self.assertNotContains(response, 'VM-password')
            self.assertNotContains(response, '192.168.1.101')

    def test_other_user_cannot_list_view_or_connect(self):
        self.client.force_login(self.bob)
        self.assertNotContains(self.client.get('/dashboard/'), 'Windows Lab')
        self.assertEqual(self.client.get(f'/servers/{self.server.pk}/').status_code, 404)
        with patch('portal.views.issue_session') as issue:
            self.assertEqual(self.client.post(f'/api/servers/{self.server.pk}/sessions/').status_code, 404)
            issue.assert_not_called()

    def test_anonymous_and_csrf_are_rejected(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get('/dashboard/').status_code, 302)
        client.force_login(self.alice)
        self.assertEqual(client.post(f'/api/servers/{self.server.pk}/sessions/').status_code, 403)
        self.assertEqual(client.get('/logout/').status_code, 405)

    @patch('portal.gateway.requests.get')
    @patch('portal.gateway.requests.post')
    def test_session_creation_uses_gateway_returned_identifier(self, post, get):
        post.return_value = Mock(json=lambda: {'authToken':'secret-token', 'dataSource':'json'})
        get.return_value = Mock(json=lambda: {'returned-connection-id': {'name':'Windows Lab'}})
        response = self.client.post(f'/api/servers/{self.server.pk}/sessions/')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['connection_id'], 'returned-connection-id')
        self.assertNotIn('VM-password', response.content.decode())
        record = RemoteSession.objects.get()
        self.assertNotEqual(record.token_encrypted, 'secret-token')
        self.assertEqual(decrypt_secret(record.token_encrypted), 'secret-token')
        # Verify what was actually sent to the gateway, using an independent decrypt.
        encoded = post.call_args.kwargs['data']['data']
        decryptor = Cipher(algorithms.AES(bytes.fromhex(settings.GUACAMOLE_JSON_SECRET)), modes.CBC(bytes(16))).decryptor()
        plain = decryptor.update(base64.b64decode(encoded)) + decryptor.finalize()
        unpad = padding.PKCS7(128).unpadder()
        signed = unpad.update(plain) + unpad.finalize()
        self.assertTrue(hmac.compare_digest(signed[:32], hmac.new(bytes.fromhex(settings.GUACAMOLE_JSON_SECRET), signed[32:], hashlib.sha256).digest()))
        payload = json.loads(signed[32:])
        self.assertEqual(list(payload['connections']), ['Windows Lab'])
        self.assertEqual(payload['connections']['Windows Lab']['parameters']['password'], 'VM-password')

    def test_gateway_gate_binds_origin_user_and_browser_session(self):
        self.record()
        headers = {'HTTP_ORIGIN': settings.PUBLIC_ORIGIN,
                   'HTTP_X_ORIGINAL_URI': '/guacamole/websocket-tunnel?token=test-gateway-token'}
        self.assertEqual(self.client.get('/api/gateway-check/', **headers).status_code, 204)
        self.assertEqual(self.client.get('/api/gateway-check/', **{**headers, 'HTTP_ORIGIN':'https://evil.example'}).status_code, 403)
        other_login = Client(); other_login.force_login(self.alice)
        self.assertEqual(other_login.get('/api/gateway-check/', **headers).status_code, 403)
        self.server.allowed_users.clear()
        self.assertEqual(self.client.get('/api/gateway-check/', **headers).status_code, 403)

    @patch('portal.gateway.requests.delete', return_value=Mock(status_code=204))
    def test_stop_revokes_token_and_is_idempotent(self, delete):
        record = self.record()
        for _ in range(2):
            self.assertEqual(self.client.post(f'/api/sessions/{record.pk}/stop/').status_code, 200)
        record.refresh_from_db()
        self.assertTrue(record.stop_requested)
        self.assertIsNotNone(record.revoked_at)
        self.assertEqual(record.token_encrypted, '')
        delete.assert_called_once()

    @patch('portal.gateway.requests.delete', return_value=Mock(status_code=204))
    def test_logout_revokes_sessions(self, delete):
        record = self.record()
        self.assertEqual(self.client.post('/logout/').status_code, 302)
        record.refresh_from_db()
        self.assertIsNotNone(record.revoked_at)
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)

    @patch('portal.gateway.requests.delete', return_value=Mock(status_code=204))
    def test_cleanup_revokes_abandoned_sessions(self, delete):
        record = self.record(last_seen=timezone.now()-timedelta(minutes=5))
        call_command('reap_sessions')
        record.refresh_from_db()
        self.assertIsNotNone(record.revoked_at)

    @patch('portal.gateway.requests.delete', return_value=Mock(status_code=503))
    def test_failed_revocation_is_marked_for_retry(self, delete):
        record = self.record()
        self.assertEqual(self.client.post(f'/api/sessions/{record.pk}/stop/').status_code, 202)
        record.refresh_from_db()
        self.assertTrue(record.stop_requested)
        self.assertIsNone(record.revoked_at)

    def test_user_cannot_stop_someone_elses_session(self):
        record = self.record()
        self.client.force_login(self.bob)
        self.assertEqual(self.client.post(f'/api/sessions/{record.pk}/stop/').status_code, 404)

    def test_admin_encrypts_password_and_blank_preserves_it(self):
        data = dict(name='New VM', operating_system='windows', protocol='rdp', hostname='192.168.1.120',
            port=3389, username='test', rdp_security='nla', enabled=True, remote_password='new-password')
        form = ServerForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        server = form.save()
        self.assertEqual(decrypt_secret(server.password_encrypted), 'new-password')
        data['remote_password'] = ''
        form = ServerForm(instance=server, data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(decrypt_secret(form.save().password_encrypted), 'new-password')

    def test_json_encryption_matches_openssl(self):
        # Differential compatibility test against OpenSSL, not just our own decoder.
        payload = {'username':'test', 'expires':1234567890, 'connections':{}}
        raw = json.dumps(payload, separators=(',', ':')).encode()
        key = settings.GUACAMOLE_JSON_SECRET
        signed = hmac.new(bytes.fromhex(key), raw, hashlib.sha256).digest() + raw
        result = subprocess.run(['openssl', 'enc', '-aes-128-cbc', '-K', key, '-iv', '00'*16],
                                input=signed, capture_output=True, check=True)
        self.assertEqual(base64.b64decode(guacamole_payload(payload)), result.stdout)
