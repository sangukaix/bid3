from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bids", "0018_savedbid_proposal_started_at"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="companyprofile",
            name="max_bid_amount",
        ),
        migrations.RemoveField(
            model_name="companyprofile",
            name="min_bid_amount",
        ),
    ]
