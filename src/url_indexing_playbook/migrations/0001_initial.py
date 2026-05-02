from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IndexingRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                (
                    "command",
                    models.CharField(
                        choices=[
                            ("ping_search_engines", "Ping search engines (GSC + IndexNow)"),
                            ("enable_crawler_hints", "Enable Cloudflare Crawler Hints + purge"),
                        ],
                        db_index=True,
                        max_length=64,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="running",
                        max_length=20,
                    ),
                ),
                ("target_count", models.IntegerField(default=0)),
                ("url_count", models.IntegerField(default=0)),
                ("gsc_attempted", models.IntegerField(default=0)),
                ("gsc_ok", models.IntegerField(default=0)),
                ("gsc_failed", models.IntegerField(default=0)),
                ("indexnow_attempted", models.IntegerField(default=0)),
                ("indexnow_ok", models.IntegerField(default=0)),
                ("indexnow_failed", models.IntegerField(default=0)),
                ("indexnow_skipped_no_key_file", models.IntegerField(default=0)),
                ("cloudflare_enable_attempted", models.IntegerField(default=0)),
                ("cloudflare_enable_ok", models.IntegerField(default=0)),
                ("cloudflare_purge_attempted", models.IntegerField(default=0)),
                ("cloudflare_purge_ok", models.IntegerField(default=0)),
                ("errors_json", models.JSONField(blank=True, default=list)),
                ("triggered_by", models.CharField(default="manual", max_length=50)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Indexing Run",
                "ordering": ["-started_at"],
                "indexes": [models.Index(fields=["command", "-started_at"], name="url_index_command_a91f3b_idx")],
            },
        ),
    ]
