"""Demo Django settings for the states_of_matter example."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "demo-only-not-for-production"
DEBUG = True
USE_TZ = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "url_indexing_playbook",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

URL_INDEXING_TARGETS = {
    "solid": {
        "domain": "solid.example.com",
        "urls": [
            "https://solid.example.com/",
            "https://solid.example.com/about/",
        ],
    },
    "liquid": {
        "domain": "liquid.example.com",
        "urls": [
            "https://liquid.example.com/",
            "https://liquid.example.com/about/",
        ],
    },
    "gas": {
        "domain": "gas.example.com",
        "urls": [
            "https://gas.example.com/",
            "https://gas.example.com/about/",
        ],
    },
    "plasma": {
        "domain": "plasma.example.com",
        "urls": [
            "https://plasma.example.com/",
            "https://plasma.example.com/about/",
        ],
    },
    "bose_einstein_condensate": {
        "domain": "bec.example.com",
        "urls": [
            "https://bec.example.com/",
            "https://bec.example.com/about/",
        ],
    },
}
