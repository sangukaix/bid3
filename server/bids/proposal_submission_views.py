from pathlib import Path
from zipfile import BadZipFile
from lxml.etree import XMLSyntaxError
from pptx.exc import PackageNotFoundError
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import BidProposal
from .services.company_knowledge import build_company_knowledge_context
from .services.proposal_submission_check import submission_report
from .services.proposal_tasks import active_task


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def submission_check(request,bid_ntce_no):
    proposal=BidProposal.objects.filter(saved_bid__user=request.user,
        saved_bid__bid_notice__bid_ntce_no=bid_ntce_no).select_related('saved_bid__bid_notice').first()
    if not proposal or not proposal.generated_file:
        return Response({'error':'점검할 제안서를 찾을 수 없습니다.'},status=404)
    if active_task(proposal.saved_bid) or (proposal.revision_plan or {}).get('status')=='generating':
        return Response({'error':'진행 중인 생성·검수가 끝난 뒤 점검해 주세요.'},status=409)
    try:
        knowledge,_=build_company_knowledge_context(request.user,prepare=False)
        report=submission_report(Path(proposal.generated_file.path).read_bytes(),proposal.revision_plan,knowledge)
    except (OSError,ValueError,KeyError,BadZipFile,XMLSyntaxError,PackageNotFoundError):
        return Response({'error':'PPTX를 읽지 못했습니다. 파일을 확인해 주세요.'},status=422)
    report.update(checked_at=timezone.now().isoformat(),bid_number=bid_ntce_no,
                  bid_title=proposal.saved_bid.bid_notice.title)
    return Response({'report':report})
