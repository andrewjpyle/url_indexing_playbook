"""pytest-django configuration."""

import django


def pytest_configure(config):
    django.setup()
