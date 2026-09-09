from django.db import migrations, models
import django.db.models.deletion
import bids.models


class Migration(migrations.Migration):

    dependencies = [
        ("bids", "0019_remove_companyprofile_bid_amounts"),
    ]

    operations = [
        migrations.CreateModel(
            name="BidQuantitativeProposal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("report", models.JSONField(default=dict)),
                ("generated_file", models.FileField(blank=True, upload_to=bids.models.bid_quantitative_upload_path)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("saved_bid", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="quantitative_proposal", to="bids.savedbid")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
    ]
