from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bids", "0011_bidproposal"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="related_industries",
            field=models.TextField(blank=True),
        ),
    ]
