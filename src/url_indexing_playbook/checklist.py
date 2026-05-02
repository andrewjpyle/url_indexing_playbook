"""Markdown deeplink generator for the manual GSC 'Request Indexing' fallback."""

import time
from pathlib import Path
from urllib.parse import quote

from url_indexing_playbook.targets import IndexingTarget

GSC_INSPECT_DEEPLINK = (
    "https://search.google.com/search-console/inspect"
    "?resource_id=sc-domain:{domain}&id={url}"
)


def generate(
    targets: list[IndexingTarget],
    output_path: str | None = None,
) -> str:
    """Write a markdown checklist of clickable GSC inspect-URL deeplinks.

    For each link below, click → in the GSC URL Inspection panel click
    "Request Indexing". This is the manual fallback for URLs that the API
    ping did not push into the crawl queue within ~7 days.

    Returns the path written to.
    """
    if output_path:
        path = output_path
    else:
        ts = time.strftime("%Y-%m-%dT%H-%M-%S")
        path = f"/tmp/gsc-checklist-{ts}.md"

    lines = [
        "# GSC Request-Indexing checklist",
        "",
        "For each link below, click → in the GSC URL Inspection panel click "
        "**Request Indexing**. This is the manual fallback for URLs that the "
        "API ping did not push into the crawl queue within ~7 days.",
        "",
        f"Hosts: {len(targets)}  URLs: {sum(len(t.urls) for t in targets)}",
        "",
    ]
    for t in targets:
        lines.append(f"## {t.domain}")
        lines.append("")
        for url in t.urls:
            deeplink = GSC_INSPECT_DEEPLINK.format(
                domain=t.domain,
                url=quote(url, safe=""),
            )
            lines.append(f"- [ ] [{url}]({deeplink})")
        lines.append("")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
