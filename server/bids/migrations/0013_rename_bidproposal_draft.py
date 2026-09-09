from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bids", "0012_companyprofile_related_industries"),
    ]

    operations = [
        migrations.RenameField(
            model_name="bidproposal",
            old_name="draft",
            new_name="revision_plan",
        ),
        migrations.AlterField(
            model_name="bidproposal",
            name="template_mode",
            field=models.CharField(default="source_revision", max_length=30),
        ),
    ]
