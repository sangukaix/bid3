from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import bids.models


class Migration(migrations.Migration):

    dependencies = [
        ("bids", "0009_recommendedbid_title_match_count"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=bids.models.company_document_upload_path)),
                ("original_name", models.CharField(max_length=255)),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("proposal", "제안서"),
                            ("company_introduction", "회사소개서"),
                        ],
                        max_length=30,
                    ),
                ),
                ("target_company", models.CharField(blank=True, max_length=200)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="company_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-uploaded_at",)},
        ),
    ]
