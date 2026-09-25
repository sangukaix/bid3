from django.core.management.base import BaseCommand
from presentation_studio.workflow import run_job


class Command(BaseCommand):
    help = 'Process one durable presentation studio job without blocking HTTP requests.'
    def add_arguments(self, parser): parser.add_argument('job_id')
    def handle(self, *args, **options): run_job(options['job_id'])
