from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("bids", "0020_bidquantitativeproposal")]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="website_url_1",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="companyprofile",
            name="website_url_2",
            field=models.URLField(blank=True),
        ),
    ]
