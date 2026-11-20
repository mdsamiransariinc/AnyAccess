"""6 component tests. Real views, ORM, crypto and gateway functions.

Only requests.post/get/delete are replaced. SQLite is disposable in-memory.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import requests
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
from portal.crypto import decrypt_secret, encrypt_secret, token_digest
from portal.models import RemoteSession, Server

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
SAFE_ERROR = 'Cannot create a remote session. Check Guacamole and the server configuration.'

class Fixtures(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('alice')
        cls.bob = User.objects.create_user('bob')
        cls.server = Server.objects.create(name='Windows Lab', operating_system='windows',
            hostname='192.0.2.10', username='labuser',
            password_encrypted=encrypt_secret('VM-password'))
        cls.server.allowed_users.add(cls.alice)

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True, raise_request_exception=False)
        self.client.get('/login/')
        self.csrf = self.client.cookies['csrftoken'].value
        self.client.force_login(self.alice)
        self.post_mock = self.start_patch('portal.gateway.requests.post')
        self.get_mock = self.start_patch('portal.gateway.requests.get')
        self.delete_mock = self.start_patch('portal.gateway.requests.delete')
        self.post_mock.return_value = Mock(json=lambda: {'authToken': 'gateway-token', 'dataSource': 'json'})
        self.get_mock.return_value = Mock(json=lambda: {'connection-42': {'name': 'Windows Lab'}})
        self.delete_mock.return_value = Mock(status_code=204)

    def start_patch(self, name):
        p = patch(name)
        value = p.start()
        self.addCleanup(p.stop)
        return value

    def post(self, url):
        return self.client.post(url, HTTP_X_CSRFTOKEN=self.csrf,
                                HTTP_ORIGIN='http://localhost:8080')

    def record(self):
        return RemoteSession.objects.create(user=self.alice, server=self.server,
            django_session_key=self.client.session.session_key,
            token_encrypted=encrypt_secret('gateway-token'),
            token_hash=token_digest('gateway-token'), last_seen=NOW,
            expires_at=NOW + timedelta(hours=1))

class CreateComponentTests(Fixtures):
    @patch('portal.gateway.timezone.now', return_value=NOW)
    def test_C01_create_persists_correct_session(self, clock):
        response = self.post(f'/api/servers/{self.server.pk}/sessions/')
        self.actual = f'HTTP {response.status_code}; rows={RemoteSession.objects.count()}'
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['connection_id'], 'connection-42')
        self.assertEqual(data['data_source'], 'json')
        self.assertEqual(data['token'], 'gateway-token')
        record = RemoteSession.objects.get()
        self.assertEqual(data['session_id'], str(record.pk))
        self.assertEqual(record.user_id, self.alice.pk)
        self.assertEqual(record.server_id, self.server.pk)
        self.assertEqual(record.django_session_key, self.client.session.session_key)
        self.assertEqual(record.expires_at, NOW + timedelta(hours=8))
        self.assertEqual(decrypt_secret(record.token_encrypted), 'gateway-token')
        self.assertNotEqual(record.token_encrypted, 'gateway-token')
        self.assertEqual(record.token_hash, token_digest('gateway-token'))
        self.assertNotIn('VM-password', response.content.decode())
        self.post_mock.assert_called_once()
        self.get_mock.assert_called_once_with(
            'http://gateway.invalid/guacamole/api/session/data/json/connections',
            params={'token': 'gateway-token'}, timeout=10)
        self.delete_mock.assert_not_called()
        self.actual += '; connection-42; owner bound; expiry +8h; token encrypted'

    def test_C02_gateway_timeout_is_safe(self):
        self.post_mock.side_effect = requests.Timeout('private upstream details')
        response = self.post(f'/api/servers/{self.server.pk}/sessions/')
        self.actual = f'HTTP {response.status_code}; rows={RemoteSession.objects.count()}'
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {'error': SAFE_ERROR})
        self.assertEqual(RemoteSession.objects.count(), 0)
        self.get_mock.assert_not_called()
        self.delete_mock.assert_not_called()
        self.actual += '; safe error; no GET/DELETE'

    def test_C03_corrupt_saved_password_is_safe(self):
        self.server.password_encrypted = 'not-a-fernet-token'
        self.server.save(update_fields=['password_encrypted'])
        response = self.post(f'/api/servers/{self.server.pk}/sessions/')
        self.actual = f'HTTP {response.status_code}; rows={RemoteSession.objects.count()}'
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {'error': SAFE_ERROR})
        self.assertEqual(RemoteSession.objects.count(), 0)
        self.post_mock.assert_not_called()
        self.get_mock.assert_not_called()
        self.delete_mock.assert_not_called()
        self.actual += '; safe error; no gateway calls'

class RevokeComponentTests(Fixtures):
    def test_C04_stop_is_persisted_and_idempotent(self):
        record = self.record()
        first = self.post(f'/api/sessions/{record.pk}/stop/')
        second = self.post(f'/api/sessions/{record.pk}/stop/')
        record.refresh_from_db()
        self.actual = f'HTTP {first.status_code}/{second.status_code}; DELETE calls={self.delete_mock.call_count}'
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), {'closed': True, 'cleanup_pending': False})
        self.assertEqual(second.json(), first.json())
        self.assertTrue(record.stop_requested)
        self.assertIsNotNone(record.revoked_at)
        self.assertEqual(record.token_encrypted, '')
        self.delete_mock.assert_called_once_with(
            'http://gateway.invalid/guacamole/api/tokens/gateway-token', timeout=5)
        self.actual += '; revoked; ciphertext cleared'

    def test_C05_gateway_failure_then_cleanup_retry(self):
        record = self.record()
        self.delete_mock.side_effect = [Mock(status_code=503), Mock(status_code=204)]
        response = self.post(f'/api/sessions/{record.pk}/stop/')
        record.refresh_from_db()
        self.actual = f'HTTP {response.status_code}; pending={record.revoked_at is None}'
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {'closed': False, 'cleanup_pending': True})
        self.assertTrue(record.stop_requested)
        self.assertIsNone(record.revoked_at)
        self.assertEqual(decrypt_secret(record.token_encrypted), 'gateway-token')
        call_command('reap_sessions')
        record.refresh_from_db()
        self.assertIsNotNone(record.revoked_at)
        self.assertEqual(record.token_encrypted, '')
        self.assertEqual(self.delete_mock.call_count, 2)
        self.actual += '; cleanup revoked; ciphertext cleared; DELETE calls=2'

    def test_C06_other_user_cannot_stop_session(self):
        record = self.record()
        old_ciphertext = record.token_encrypted
        self.client.force_login(self.bob)
        response = self.post(f'/api/sessions/{record.pk}/stop/')
        record.refresh_from_db()
        self.actual = f'HTTP {response.status_code}; DELETE calls={self.delete_mock.call_count}'
        self.assertEqual(response.status_code, 404)
        self.assertFalse(record.stop_requested)
        self.assertIsNone(record.revoked_at)
        self.assertEqual(record.token_encrypted, old_ciphertext)
        self.delete_mock.assert_not_called()
        self.actual += '; record unchanged'
