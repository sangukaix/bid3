"""Detached proposal workers, following the presentation studio's local process pattern."""
import os
import subprocess
import sys
from contextvars import ContextVar
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from ..models import ProposalTask, BidProposal, CompanyProfile

CURRENT_TASK = ContextVar('bid_proposal_task',default=None)


def report_progress(message):
    task_id=CURRENT_TASK.get()
    if task_id is None:
        return
    task=ProposalTask.objects.filter(pk=task_id,status='running').first()
    if task:
        ProposalTask.objects.filter(pk=task_id,status='running').update(
            payload={**task.payload,'progress':message},updated_at=timezone.now())


def active_task(saved_bid):
    return ProposalTask.objects.filter(saved_bid=saved_bid,status__in=['queued','running']).first()


def process_alive(pid):
    if not pid:
        return True
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        library=ctypes.WinDLL('kernel32',use_last_error=True)
        library.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        library.OpenProcess.restype=wintypes.HANDLE
        library.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        library.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=library.OpenProcess(0x1000,False,pid)
        if not handle:
            return ctypes.get_last_error()!=87  # Access denied is not proof of death.
        code=wintypes.DWORD()
        try:
            return not library.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value==259
        finally:
            library.CloseHandle(handle)
    try:
        os.kill(pid,0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def recover_dead_task(task):
    dead=task.status=='running' and not process_alive(task.worker_pid)
    lost=task.status=='queued' and task.created_at<timezone.now()-timedelta(minutes=3)
    if dead or lost:
        if ProposalTask.objects.filter(pk=task.pk,status=task.status).update(status='failed',
                error='작업 프로세스가 중단되었습니다. 원래 파일을 확인하고 다시 요청해 주세요.',updated_at=timezone.now()):
            proposal=BidProposal.objects.filter(saved_bid=task.saved_bid).first()
            if proposal and (proposal.revision_plan or {}).get('status')=='generating':
                proposal.revision_plan['status']=task.payload.get('previous_status','draft')
                proposal.save(update_fields=['revision_plan','updated_at'])
        task.refresh_from_db()
    return task


def enqueue(saved_bid,kind,payload):
    current=active_task(saved_bid)
    if current:
        recover_dead_task(current)
        if current.status in {'queued','running'}:
            if current.kind!=kind:
                raise ValueError('진행 중인 생성·검수가 끝난 뒤 요청해 주세요.')
            return current
    proposal=BidProposal.objects.filter(saved_bid=saved_bid).first()
    payload={**payload,'previous_status':(proposal.revision_plan or {}).get('status','draft') if proposal else 'draft',
             'proposal_updated_at':proposal.updated_at.isoformat() if proposal else None}
    try:
        with transaction.atomic():
            task=ProposalTask.objects.create(saved_bid=saved_bid,kind=kind,payload=payload)
    except IntegrityError:
        current=active_task(saved_bid)
        if current and current.kind==kind:
            return current
        raise ValueError('다른 생성·검수가 먼저 시작되었습니다.')
    try:
        log_root=Path(settings.MEDIA_ROOT)/'proposal_task_logs';log_root.mkdir(parents=True,exist_ok=True)
        with (log_root/f'{task.pk}.log').open('ab') as log:
            subprocess.Popen([sys.executable,str(settings.BASE_DIR/'manage.py'),'proposal_task',str(task.pk)],
                cwd=settings.BASE_DIR,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,start_new_session=os.name!='nt')
    except OSError:
        task.status='failed';task.error='작업 프로세스를 시작하지 못했습니다.';task.save()
        raise ValueError(task.error)
    return task


def run_task(task_id):
    if not ProposalTask.objects.filter(pk=task_id,status='queued').update(status='running',worker_pid=os.getpid(),updated_at=timezone.now()):
        return
    task=ProposalTask.objects.select_related('saved_bid__user','saved_bid__bid_notice').get(pk=task_id)
    token=CURRENT_TASK.set(task.pk)
    try:
        proposal=BidProposal.objects.filter(saved_bid=task.saved_bid).select_related('saved_bid__bid_notice').first()
        if (proposal.updated_at.isoformat() if proposal else None)!=task.payload['proposal_updated_at']:
            raise ValueError('시작 전에 제안서가 변경되었습니다. 최신 파일로 다시 요청해 주세요.')
        if not task.saved_bid.user.is_active or task.saved_bid.proposal_trashed_at:
            raise ValueError('계정 또는 프로젝트 상태가 변경되었습니다.')
        if task.kind=='generate':
            from ..views import generate_saved_proposal
            profile=CompanyProfile.objects.filter(user=task.saved_bid.user).first()
            if profile is None:
                raise ValueError('회사 정보를 입력해 주세요.')
            response=generate_saved_proposal(task.saved_bid,profile,task.payload['template_id'],proposal)
        elif task.kind=='review':
            from ..proposal_review_views import review_saved_proposal
            if not proposal or not proposal.generated_file:
                raise ValueError('검수할 파일이 없습니다.')
            response=review_saved_proposal(proposal,task.saved_bid.user)
        else:
            raise ValueError('지원하지 않는 작업입니다.')
        if response.status_code>=400:
            raise ValueError(response.data.get('error','작업을 완료하지 못했습니다.'))
        ProposalTask.objects.filter(pk=task.pk,status='running').update(status='completed',updated_at=timezone.now())
    except Exception as error:
        proposal=BidProposal.objects.filter(saved_bid=task.saved_bid).first()
        if proposal and (proposal.revision_plan or {}).get('status')=='generating':
            proposal.revision_plan['status']=task.payload.get('previous_status','draft')
            proposal.save(update_fields=['revision_plan','updated_at'])
        detail=str(error) if isinstance(error,ValueError) else f'작업 실패 ({type(error).__name__}). 원래 파일을 확인해 주세요.'
        ProposalTask.objects.filter(pk=task.pk,status='running').update(status='failed',error=detail[:1000],updated_at=timezone.now())
    finally:
        CURRENT_TASK.reset(token)
