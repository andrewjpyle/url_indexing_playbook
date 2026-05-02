"""IndexingRun: per-invocation audit log."""

from django.db import models


class IndexingRun(models.Model):
    """Records every run of a url_indexing_playbook management command."""

    COMMAND_CHOICES = [
        ("ping_search_engines", "Ping search engines (GSC + IndexNow)"),
        ("enable_crawler_hints", "Enable Cloudflare Crawler Hints + purge"),
    ]

    STATUS_CHOICES = [
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    command = models.CharField(max_length=64, choices=COMMAND_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")

    target_count = models.IntegerField(default=0)
    url_count = models.IntegerField(default=0)

    gsc_attempted = models.IntegerField(default=0)
    gsc_ok = models.IntegerField(default=0)
    gsc_failed = models.IntegerField(default=0)

    indexnow_attempted = models.IntegerField(default=0)
    indexnow_ok = models.IntegerField(default=0)
    indexnow_failed = models.IntegerField(default=0)
    indexnow_skipped_no_key_file = models.IntegerField(default=0)

    cloudflare_enable_attempted = models.IntegerField(default=0)
    cloudflare_enable_ok = models.IntegerField(default=0)
    cloudflare_purge_attempted = models.IntegerField(default=0)
    cloudflare_purge_ok = models.IntegerField(default=0)

    errors_json = models.JSONField(default=list, blank=True)

    triggered_by = models.CharField(max_length=50, default="manual")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Indexing Run"
        indexes = [
            models.Index(fields=["command", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.command} — {self.target_count} hosts ({self.status})"
