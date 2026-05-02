"""Minimal Django settings for the test suite."""

SECRET_KEY = "test-key-not-secret"
DEBUG = True
USE_TZ = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "url_indexing_playbook",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

URL_INDEXING_TARGETS = {
    "site_a": {
        "domain": "a.example.com",
        "urls": [
            "https://a.example.com/page-1/",
            "https://a.example.com/page-2/",
        ],
    },
    "site_b": {
        "domain": "b.example.com",
        "urls": ["https://b.example.com/"],
    },
}
