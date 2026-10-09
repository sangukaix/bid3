"""Read-only AI audit of an existing owner-scoped PPTX; never rewrite or finalize it."""
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
from datetime import timedelta
from zipfile import BadZipFile
from lxml.etree import XMLSyntaxError
from pptx.exc import PackageNotFoundError
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import BidProposal
from .services.company_knowledge import build_company_knowledge_context
from .services.proposal_final_review import verify_artifact, inventory_bytes, invalidate_final_review
from .services.proposal_planning import build_writing_plan
from .services.proposal_pptx_renderer import inspect_proposal_quality
from .services.llm import build_text_model


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def full_review(request, bid_ntce_no):
    proposal=BidProposal.objects.filter(saved_bid__user=request.user,
        saved_bid__bid_notice__bid_ntce_no=bid_ntce_no).select_related('saved_bid').first()
    if not proposal or not proposal.generated_file:
        return Response({'error':'검수할 제안서를 찾을 수 없습니다.'},status=404)
    if (proposal.revision_plan or {}).get('status')=='generating':
        return Response({'error':'생성이 끝난 뒤 검수해 주세요.'},status=409)
    if request.data.get('async') is True:
        from .proposal_task_views import enqueue_response
        return enqueue_response(proposal.saved_bid, 'review', {})
    from .models import ProposalTask
    if ProposalTask.objects.filter(saved_bid=proposal.saved_bid,status__in=['queued','running']).exists():
        return Response({'error':'진행 중인 생성·검수가 끝난 뒤 다시 요청해 주세요.'},status=409)
    return review_saved_proposal(proposal, request.user)


def review_saved_proposal(proposal, user):
    try:
        content=Path(proposal.generated_file.path).read_bytes()
        plan=deepcopy(proposal.revision_plan or {})
        knowledge,_=build_company_knowledge_context(user,prepare=False)
        coverage=build_text_model('PROPOSAL','gpt-5.6-sol',3500,reasoning_effort='none')
        claims=build_text_model('CLAIM_REVIEW','gpt-4o-mini',3000,reasoning_effort='none')
        # Existing file planning uses current output numbers, with no rewriting.
        plan['writing_plan']=build_writing_plan(plan.get('requirement_register',{}),inventory_bytes(content),knowledge,coverage)
        for row in plan['writing_plan']['items']:
            row['output_slide_numbers']=row['source_slide_numbers']
        verify_artifact(content,plan,knowledge,coverage,claims)
        plan['quality_review']=inspect_proposal_quality(content)
        current,_=build_company_knowledge_context(user,prepare=False)
        invalidate_final_review(content,plan,current)
        # Also catch external file replacement without a DB timestamp change.
        if sha256(Path(proposal.generated_file.path).read_bytes()).digest()!=sha256(content).digest():
            return Response({'error':'검수 중 파일이 변경되었습니다. 다시 검수해 주세요.'},status=409)
    except (OSError,ValueError,KeyError,BadZipFile,XMLSyntaxError,PackageNotFoundError):
        return Response({'error':'PPTX 또는 AI 검수 설정을 확인해 주세요.'},status=422)
    updated=BidProposal.objects.filter(pk=proposal.pk,updated_at=proposal.updated_at,
        generated_file=proposal.generated_file.name).update(revision_plan=plan,
        updated_at=max(timezone.now(),proposal.updated_at+timedelta(microseconds=1)))
    if not updated:
        return Response({'error':'검수 중 제안서가 수정·확정되었습니다. 다시 불러와 주세요.'},status=409)
    proposal.refresh_from_db()
    from .views import serialize_bid_proposal
    return Response({'proposal':serialize_bid_proposal(proposal)})
