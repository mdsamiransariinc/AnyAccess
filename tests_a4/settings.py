"""Test-only settings. Never imports production settings or reads .env."""
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
SECRET_KEY = 'assignment4-public-test-only-key-not-for-deployment'
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost']
PUBLIC_ORIGIN = 'http://localhost:8080'
CSRF_TRUSTED_ORIGINS = [PUBLIC_ORIGIN]
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth',
    'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.messages', 'django.contrib.staticfiles', 'portal',
]
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:',
    'TEST': {'NAME': ':memory:'},
}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
STATIC_URL = '/static/'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
LOGIN_REDIRECT_URL = '/dashboard/'
LOGIN_URL = '/login/'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.PBKDF2PasswordHasher']
CREDENTIAL_KEY = 'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8='
GUACAMOLE_JSON_SECRET = '00112233445566778899aabbccddeeff'
GUACAMOLE_URL = 'http://gateway.invalid/guacamole'
REMOTE_SESSION_SECONDS = 8 * 60 * 60
REMOTE_HEARTBEAT_GRACE = 120
