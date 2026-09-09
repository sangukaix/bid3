from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bids", "0008_bidchatmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="recommendedbid",
            name="title_match_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
