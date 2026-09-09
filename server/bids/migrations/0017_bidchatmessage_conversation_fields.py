from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bids", "0016_remove_companydocument_target_company"),
    ]

    operations = [
        migrations.AddField(
            model_name="bidchatmessage",
            name="message_type",
            field=models.CharField(
                choices=[
                    ("question", "공고 질문"),
                    ("proposal", "제안서 수정"),
                ],
                default="question",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="bidchatmessage",
            name="status",
            field=models.CharField(
                choices=[
                    ("applied", "처리 완료"),
                    ("pending", "반영 대기"),
                    ("failed", "처리 실패"),
                ],
                default="applied",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="bidchatmessage",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="bidchatmessage",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
