#!/usr/bin/env python
"""Django manage.py for the states_of_matter demo."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
