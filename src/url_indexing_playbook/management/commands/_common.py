"""Shared helpers for the three management commands."""

import importlib
from collections.abc import Callable
from typing import Any

from url_indexing_playbook.adapters import DefaultTargetSource
from url_indexing_playbook.targets import TargetSource

DEFAULT_TARGET_SOURCE = "url_indexing_playbook.adapters.DefaultTargetSource"


def load_target_source(dotted_path: str) -> TargetSource:
    """Resolve a dotted path to a TargetSource and instantiate it.

    For the default source, returns DefaultTargetSource() with no args.
    For custom sources, the class must be no-arg-instantiable.
    """
    if dotted_path == DEFAULT_TARGET_SOURCE:
        return DefaultTargetSource()
    module_path, _, attr = dotted_path.rpartition(".")
    if not module_path:
        raise ValueError(f"Invalid target-source path: {dotted_path}")
    module = importlib.import_module(module_path)
    cls = getattr(module, attr)
    return cls()


def load_callable(dotted_path: str) -> Callable[..., Any]:
    """Resolve a dotted path to a callable (function or class)."""
    module_path, _, attr = dotted_path.rpartition(".")
    if not module_path:
        raise ValueError(f"Invalid callable path: {dotted_path}")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def parse_slugs(value: str) -> list[str] | None:
    """Parse a comma-separated --slugs flag into a list, or None if empty."""
    if not value:
        return None
    return [s.strip() for s in value.split(",") if s.strip()]
