"""Target source contract — implement against your own model, or use the default."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class IndexingTarget:
    """One host + its URLs to surface to search engines.

    The adapter's job is to turn whatever model you have into one of these.
    """

    slug: str
    domain: str
    urls: list[str]
    # Override the GSC site_url; defaults to f"sc-domain:{domain}" if blank.
    gsc_site_url: str = ""
    # Free-form bag for adapter authors.
    extra: dict = field(default_factory=dict)

    @property
    def effective_gsc_site_url(self) -> str:
        return self.gsc_site_url or f"sc-domain:{self.domain}"


class TargetSource(ABC):
    """Implement this against your own model.

    For users without an existing model, see
    `url_indexing_playbook.adapters.DefaultTargetSource`.
    """

    @abstractmethod
    def iter_targets(
        self,
        *,
        slugs: list[str] | None = None,
    ) -> Iterable[IndexingTarget]:
        """Yield IndexingTarget instances. Filter by slug if `slugs` is given."""
