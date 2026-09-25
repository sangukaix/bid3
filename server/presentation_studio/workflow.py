from contextlib import contextmanager
from pathlib import Path
import os
import hashlib
import json
import traceback
import subprocess
import sys
import time

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction, IntegrityError
from django.utils import timezone
import pypdfium2 as pdfium

from .models import Project, Revision, Message, Job
from .decks import Deck, inventory, assert_protected


def require_idle(project):
    # A detached worker survives a browser/server restart. Interrupted jobs can
    # be cancelled and retried, and never leave half-written revisions active.
    if project.jobs.filter(status__in=['queued','running']).exists():
        raise ValueError('현재 작업이 끝난 뒤 수정하거나 작업을 취소해 주세요.')


def save_revision(project, content, label, expected=None, protected=None, job=None):
    slides=inventory(content)
    with transaction.atomic():
        project=Project.objects.select_for_update().get(pk=project.pk)
        if expected is not None and project.current_id!=expected: raise ValueError('다른 수정본이 저장되었습니다. 최신 버전에서 다시 요청해 주세요.')
        if job and not Job.objects.filter(pk=job.pk,status='running').exists(): raise ValueError('작업이 취소되었습니다.')
        if not job: require_idle(project)
        if project.current and protected is None:
            assert_protected(Path(project.current.file.path).read_bytes(),content,project.protected_slides)
        elif project.current:
            # Reordering remaps locks; verify the original protected content is
            # still represented before accepting caller-supplied new numbers.
            from .decks import rel_path
            old=Deck(Path(project.current.file.path).read_bytes()); new=Deck(content)
            for number in project.protected_slides:
                old_part=old.slide_parts()[number-1]
                if not any(old.parts[old_part]==new.parts[new.slide_parts()[n-1]] and old.parts.get(rel_path(old_part))==new.parts.get(rel_path(new.slide_parts()[n-1])) for n in protected):
                    raise ValueError('유지 페이지 설정이 바뀌었습니다. 최신 버전에서 다시 요청하세요.')
        number=(project.revisions.order_by('-number').values_list('number',flat=True).first() or 0)+1
        revision=Revision(project=project,number=number,label=label[:250],inventory=slides)
        revision.file.save('presentation.pptx',ContentFile(content),save=False); revision.save()
        project.current=revision
        if protected is not None: project.protected_slides=protected
        project.save(update_fields=['current','protected_slides','updated_at'])
        return revision


def configuration_signature(project):
    state={'title':project.title,'audience':project.audience,'instruction':project.instruction,'protected_slides':project.protected_slides,
           'references':list(project.references.order_by('id').values('id','kind','name','locator','enabled','digest'))}
    return hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()


def validate_plan(project, plan):
    if plan.get('questions'): raise ValueError('AI 질문에 먼저 답한 뒤 새 작성안을 받아 주세요.')
    if plan.get('base_revision')!=project.current_id: raise ValueError('이 작성안 이후 파일이 바뀌었습니다. 최신 버전으로 다시 요청하세요.')
    if not project.template_confirmed: raise ValueError('현재 디자인과 유지할 페이지를 먼저 확인해 주세요.')
    if plan.get('configuration_signature') and plan['configuration_signature']!=configuration_signature(project): raise ValueError('작성안 이후 지침·참고자료·유지 설정이 바뀌었습니다. 새 작성안을 받아 주세요.')
    mode=plan.get('mode')
    if mode not in {'discuss','revise','continue','rewrite'}: raise ValueError('작성 범위가 없는 계획입니다. 다시 요청해 주세요.')
    changes=plan.get('changes',[]); additions=plan.get('additions',[]); rewrite=plan.get('rewrite_slides',[])
    if mode=='discuss' and (changes or additions or rewrite): raise ValueError('의논 모드에서는 파일을 수정하지 않습니다. 현재 페이지 수정 또는 이어 만들기를 선택하세요.')
    if mode=='continue' and (changes or rewrite or len(additions)!=plan.get('append_count')): raise ValueError('이어 만들기 작성안이 기존 페이지를 변경하거나 요청 장수와 다릅니다. 다시 요청해 주세요.')
    if mode=='revise' and (additions or rewrite or any(c['slide']!=plan.get('selected_slide') for c in changes)): raise ValueError('현재 페이지 이외의 수정이 포함되었습니다. 다시 요청해 주세요.')
    if mode=='rewrite' and (changes or additions or sorted(rewrite)!=[s['number'] for s in project.current.inventory if s['number'] not in project.protected_slides]): raise ValueError('재작성 범위와 현재 유지 설정이 다릅니다. 다시 요청해 주세요.')
    if len(additions)>10: raise ValueError('한 번에 최대 10쪽을 추가할 수 있습니다.')
    for change in plan.get('changes',[]):
        number=int(change['slide'])
        if number in project.protected_slides: raise ValueError(f'{number}페이지는 유지하도록 잠겨 있습니다.')
        if not 1<=number<=len(project.current.inventory): raise ValueError('작성안의 페이지 번호가 올바르지 않습니다.')
        valid={e['target'] for e in project.current.inventory[number-1]['elements']}
        if any(e['target'] not in valid for e in change.get('edits',[])): raise ValueError('작성안에 없는 텍스트 위치가 포함되어 있습니다.')
    for number in plan.get('rewrite_slides',[]):
        if number in project.protected_slides or not 1<=number<=len(project.current.inventory): raise ValueError('작성할 페이지의 유지 설정을 다시 확인하세요.')
    for addition in plan.get('additions',[]):
        if not 1<=addition['template_slide']<=len(project.current.inventory): raise ValueError('복제할 디자인 페이지를 찾을 수 없습니다.')
    if len(project.current.inventory)+len(plan.get('additions',[]))>80: raise ValueError('전체 페이지 수는 80쪽 이하입니다.')


def enqueue(project, kind, payload):
    try:
        with transaction.atomic():
            locked=Project.objects.select_for_update().get(pk=project.pk)
            require_idle(locked)
            job=Job.objects.create(project=locked,kind=kind,payload=payload)
    except IntegrityError as error: raise ValueError('다른 작업이 진행 중입니다.') from error
    if getattr(settings,'STUDIO_INLINE_JOBS',False):
        run_job(job.id)
    else:
        try:
            subprocess.Popen([sys.executable,str(settings.BASE_DIR/'manage.py'),'presentation_job',str(job.id)],
                cwd=settings.BASE_DIR,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,start_new_session=os.name!='nt')
        except OSError:
            job.status='failed'; job.error='작업 프로세스를 실행하지 못했습니다. 서버 실행 환경을 확인하세요.'; job.save()
    return job


def progress(job,text):
    if not Job.objects.filter(pk=job.pk,status='running').update(progress=text,updated_at=timezone.now()):
        raise ValueError('작업이 취소되었습니다.')


def preview_directory(revision):
    return Path(settings.MEDIA_ROOT)/'presentation_previews'/str(revision.id)


@contextmanager
def office_lock():
    root=Path(settings.MEDIA_ROOT)/'presentation_previews'; root.mkdir(parents=True,exist_ok=True)
    with (root/'office.lock').open('a+b') as handle:
        handle.seek(0); handle.write(b'0'); handle.flush(); handle.seek(0)
        began=time.monotonic()
        while True:
            try:
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic()-began>180: raise ValueError('다른 미리보기 작업이 오래 걸리고 있습니다. 잠시 후 다시 시도하세요.')
                time.sleep(.3)
        try: yield
        finally:
            handle.seek(0)
            if os.name=='nt': msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


def render(revision):
    from bids.services.proposal_preview import _convert_with_libreoffice, _convert_with_powerpoint
    directory=preview_directory(revision)
    if (directory/'ready').exists(): return
    with office_lock():
        if (directory/'ready').exists(): return
        directory.mkdir(parents=True,exist_ok=True); pdf=directory/'presentation.pdf'
        if not (_convert_with_libreoffice(Path(revision.file.path),pdf) or _convert_with_powerpoint(Path(revision.file.path),pdf)):
            raise ValueError('미리보기에는 서버 PC의 PowerPoint 또는 LibreOffice가 필요합니다. PPTX 다운로드는 사용할 수 있습니다.')
        with pdfium.PdfDocument(str(pdf)) as document:
            if len(document)!=len(revision.inventory): raise ValueError('변환된 미리보기의 페이지 수가 맞지 않습니다. PPTX를 확인해 주세요.')
            for index in range(len(document)):
                page=document[index]; bitmap=page.render(scale=1.4); image=bitmap.to_pil()
                try: image.save(directory/f'{index+1}.png')
                finally: image.close(); bitmap.close(); page.close()
        (directory/'ready').write_text('ok')


def run_job(job_id):
    if not Job.objects.filter(pk=job_id,status='queued').update(status='running',worker_pid=os.getpid(),updated_at=timezone.now()): return
    job=Job.objects.select_related('project__current','project__owner').get(pk=job_id)
    project=job.project
    try:
        if job.kind=='preview':
            revision=project.revisions.get(pk=job.payload['revision']); progress(job,'페이지 미리보기 변환 중'); render(revision)
        elif job.kind=='chat':
            from .ai import plan
            progress(job,'Gemma4가 참고자료와 요청을 검토하고 있습니다')
            result=plan(project,job.payload)
            if not Job.objects.filter(pk=job.pk,status='running').exists(): return
            Message.objects.create(project=project,role='assistant',content=result['message'],plan=result)
        elif job.kind=='apply':
            from .ai import context, fill_page
            message=project.messages.get(pk=job.payload['message'])
            plan=message.plan; validate_plan(project,plan)
            original=Path(project.current.file.path).read_bytes(); deck=Deck(original)
            for change in plan.get('changes',[]): deck.edit(change['slide'],change['edits'])
            packet=context(project,plan.get('request',''))
            validate_plan(project,plan)  # Sources may have changed during refresh.
            for number in plan.get('rewrite_slides',[]):
                progress(job,f'{number}페이지 작성 중 · 잠긴 페이지는 유지합니다')
                result=fill_page(project,project.current.inventory[number-1],plan.get('request',''),packet)
                if result['questions']:
                    Message.objects.create(project=project,role='assistant',content='작성 전에 확인이 필요합니다.',plan={'questions':result['questions']})
                    raise ValueError('AI가 추가 확인을 요청했습니다. 대화에서 답해 주세요. 원본은 유지했습니다.')
                deck.edit(number,result['edits'])
            for index,addition in enumerate(plan.get('additions',[]),1):
                progress(job,f'추가 페이지 {index}/{len(plan["additions"])} 작성 중')
                number=deck.clone(addition['template_slide'])
                slide={**project.current.inventory[addition['template_slide']-1],'number':number}
                result=fill_page(project,slide,f'{addition["title"]}\n{addition["brief"]}',packet)
                if result['questions']:
                    Message.objects.create(project=project,role='assistant',content='새 페이지를 만들기 전에 확인해 주세요.',plan={'questions':result['questions']})
                    raise ValueError('추가 질문이 있습니다. 대화에서 답한 뒤 다시 요청하세요. 원본은 유지했습니다.')
                deck.edit(number,result['edits'])
            content=deck.bytes(); assert_protected(original,content,project.protected_slides)
            progress(job,'수정본 저장 중')
            revision=save_revision(project,content,'Gemma4 작성안 적용',expected=plan['base_revision'],job=job)
            message.applied_revision=revision; message.save(update_fields=['applied_revision'])
            try:
                progress(job,'새 버전의 페이지 미리보기 생성 중'); render(revision)
            except Exception:
                Message.objects.create(project=project,role='assistant',content='PPTX 수정본은 저장했습니다. 미리보기 변환에 실패하면 PPTX를 내려받거나 미리보기를 다시 시도하세요.')
        else: raise ValueError('지원하지 않는 작업입니다.')
        Job.objects.filter(pk=job.pk,status='running').update(status='completed',progress='완료',updated_at=timezone.now())
    except Exception as error:
        log_root=Path(settings.MEDIA_ROOT)/'presentation_job_logs'; log_root.mkdir(parents=True,exist_ok=True)
        (log_root/f'{job.id}.log').write_text(traceback.format_exc(),encoding='utf-8')
        detail=str(error) if isinstance(error,ValueError) else '작업 처리에 실패했습니다. Ollama 연결과 파일을 확인한 뒤 다시 시도해 주세요.'
        Job.objects.filter(pk=job.pk,status='running').update(status='failed',error=detail[:1200],progress='작업 실패 · 이전 파일 보존',updated_at=timezone.now())
