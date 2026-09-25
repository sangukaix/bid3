import uuid
from django.conf import settings
from django.db import models


def stored_file(instance, filename):
    # Filenames supplied by users never become storage paths.
    suffix = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'
    return f"presentation_studio/{uuid.uuid4().hex}.{suffix}"


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    instruction = models.TextField(blank=True)
    audience = models.CharField(max_length=300, blank=True)
    template_confirmed = models.BooleanField(default=False)
    protected_slides = models.JSONField(default=list)
    current = models.ForeignKey('Revision', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Revision(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='revisions')
    file = models.FileField(upload_to=stored_file)
    number = models.PositiveIntegerField()
    label = models.CharField(max_length=250)
    inventory = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project', 'number'], name='studio_revision_number')]


class PersonalTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to=stored_file)
    protected_slides = models.JSONField(default=list)
    slide_count = models.PositiveIntegerField()
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Reference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='references')
    kind = models.CharField(max_length=20)  # upload, text, url, path
    name = models.CharField(max_length=250)
    locator = models.TextField(blank=True)
    file = models.FileField(upload_to=stored_file, blank=True)
    text = models.TextField(blank=True)
    digest = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class Message(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=12)
    content = models.TextField()
    plan = models.JSONField(default=dict)
    applied_revision = models.ForeignKey(Revision, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='jobs')
    kind = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default='queued')
    payload = models.JSONField(default=dict)
    progress = models.CharField(max_length=250, default='작업 준비 중')
    error = models.TextField(blank=True)
    worker_pid = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project'], condition=models.Q(status__in=['queued', 'running']), name='studio_one_active_job')]
