from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("bids", "0007_companyprofile_excluded_keywords_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="BidChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "사용자"), ("assistant", "AI")], max_length=10)),
                ("content", models.TextField()),
                ("sources", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("saved_bid", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_messages", to="bids.savedbid")),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
