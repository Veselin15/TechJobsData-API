from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="APIRequestLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(max_length=10)),
                ("endpoint", models.CharField(max_length=255)),
                ("status_code", models.PositiveSmallIntegerField()),
                (
                    "plan_type",
                    models.CharField(
                        choices=[("free", "Free"), ("pro", "Pro"), ("business", "Business")],
                        default="free",
                        max_length=20,
                    ),
                ),
                ("api_key_prefix", models.CharField(blank=True, default="", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_request_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user", "-created_at"], name="core_apireq_user_id_90d95c_idx"),
                    models.Index(fields=["plan_type", "-created_at"], name="core_apireq_plan_ty_eb77c9_idx"),
                ],
            },
        ),
    ]
