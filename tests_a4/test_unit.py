"""12 unit tests. Database access is forbidden by SimpleTestCase."""
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch
from cryptography.fernet import InvalidToken
from django.test import SimpleTestCase, override_settings
from portal.models import Server
from portal.crypto import decrypt_secret, guacamole_payload, token_digest

TOKEN = ('gAAAAABq_FyyiqAQMAxlrhxFk31qr5eQ1ujcPCBspNYq57CV5p1-X0jFYN7'
         'BreWdmyUxq6hTJYc4DS9Qhc5Dz4HiSvH03m28TA==')
VECTOR = ('cYnKgo5dQmYyzcxkAAE4Zp6l0SvEeAAebRt6oefYwgAtW9UDwJ4Axeb6fGZm'
          '/NhUTNMknNWlHaM70nct60E0Ceuf/g/lewhytpUYp0Jz77o=')
EMPTY_VECTOR = '+JoC5b2/f1zm7E/A9Yb/Nb2cK+3Pq60oyWki1kOVt3yU2rUoy4+KfwDQTkLt2leb'

class AccessUnitTests(SimpleTestCase):
    def setUp(self):
        self.server = Server(name='Lab', enabled=True)
        self.user = SimpleNamespace(pk=7, is_authenticated=True,
                                    is_active=True, is_superuser=False)
        self.manager = Mock()
        fake = PropertyMock(return_value=self.manager)
        self.descriptor = patch.object(Server, 'allowed_users', fake)
        self.descriptor.start()
        self.addCleanup(self.descriptor.stop)

    def test_U01_assigned_user_allowed(self):
        self.manager.filter.return_value.exists.return_value = True
        actual = self.server.can_access(self.user)
        self.actual = f'access={actual}; lookup user=7'
        self.assertIs(actual, True)
        self.manager.filter.assert_called_once_with(pk=7)

    def test_U02_unassigned_user_denied(self):
        self.manager.filter.return_value.exists.return_value = False
        actual = self.server.can_access(self.user)
        self.actual = f'access={actual}; assignment absent'
        self.assertIs(actual, False)
        self.manager.filter.assert_called_once_with(pk=7)

    def test_U03_disabled_server_denies_superuser(self):
        self.server.enabled = False
        self.user.is_superuser = True
        actual = self.server.can_access(self.user)
        self.actual = f'access={actual}; assignment lookups={self.manager.filter.call_count}'
        self.assertIs(actual, False)
        self.manager.filter.assert_not_called()

class DigestUnitTests(SimpleTestCase):
    def test_U04_known_sha256(self):
        actual = token_digest('abc')
        self.actual = actual
        self.assertEqual(actual, 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_U05_empty_token_digest(self):
        actual = token_digest('')
        self.actual = actual
        self.assertEqual(actual, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    def test_U06_none_is_not_a_string(self):
        with self.assertRaises(AttributeError) as raised:
            token_digest(None)
        self.actual = type(raised.exception).__name__

class DecryptUnitTests(SimpleTestCase):
    def test_U07_decrypt_known_fixture(self):
        actual = decrypt_secret(TOKEN)
        self.actual = actual
        self.assertEqual(actual, 'lab-password')

    def test_U08_empty_ciphertext_rejected(self):
        with self.assertRaises(InvalidToken) as raised:
            decrypt_secret('')
        self.actual = type(raised.exception).__name__

    @override_settings(CREDENTIAL_KEY='__________________________________________8=')
    def test_U09_wrong_key_rejected(self):
        with self.assertRaises(InvalidToken) as raised:
            decrypt_secret(TOKEN)
        self.actual = type(raised.exception).__name__

class PayloadUnitTests(SimpleTestCase):
    def test_U10_payload_matches_independent_vector(self):
        actual = guacamole_payload({'username': 'student', 'connections': {}})
        self.actual = 'Exact V1 match' if actual == VECTOR else actual
        self.assertEqual(actual, VECTOR)

    def test_U11_empty_object_matches_vector(self):
        actual = guacamole_payload({})
        self.actual = 'Exact V2 match' if actual == EMPTY_VECTOR else actual
        self.assertEqual(actual, EMPTY_VECTOR)

    @override_settings(GUACAMOLE_JSON_SECRET='00' * 15)
    def test_U12_short_key_rejected(self):
        with self.assertRaisesMessage(ValueError,
                'GUACAMOLE_JSON_SECRET must contain 32 hexadecimal characters') as raised:
            guacamole_payload({})
        self.actual = type(raised.exception).__name__ + ': ' + str(raised.exception)
