from django.core.management.base import BaseCommand
from bids.services.proposal_tasks import run_task


class Command(BaseCommand):
    help='Run one durable proposal generation or review task.'

    def add_arguments(self,parser):
        parser.add_argument('task_id',type=int)

    def handle(self,*args,**options):
        run_task(options['task_id'])
