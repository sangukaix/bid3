from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bids", "0017_bidchatmessage_conversation_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="savedbid",
            name="proposal_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
