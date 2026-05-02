"""url_indexing_playbook — ping search engines about your new URLs."""

from url_indexing_playbook.targets import IndexingTarget, TargetSource

__all__ = ["IndexingTarget", "TargetSource"]
__version__ = "0.1.0.dev0"

default_app_config = "url_indexing_playbook.apps.UrlIndexingPlaybookConfig"
