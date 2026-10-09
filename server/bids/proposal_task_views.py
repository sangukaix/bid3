from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import SavedBid, BidProposal
from .services.proposal_tasks import enqueue, recover_dead_task


def task_data(task):
    return {'id':task.pk,'kind':task.kind,'status':task.status,'error':task.error,
            'progress':task.payload.get('progress','문서 작성·검수 진행 중' if task.status=='running' else '작업 시작 준비'), 'updated_at':task.updated_at}


def enqueue_response(saved_bid,kind,payload):
    try:
        task=enqueue(saved_bid,kind,payload)
    except ValueError as error:
        return Response({'error':str(error)},status=409)
    return Response({'task':task_data(task)},status=202)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_status(request,bid_ntce_no):
    saved=SavedBid.objects.filter(user=request.user,bid_notice__bid_ntce_no=bid_ntce_no).first()
    if not saved:
        return Response({'error':'프로젝트를 찾을 수 없습니다.'},status=404)
    task=saved.proposal_tasks.order_by('-created_at').first()
    if task:
        recover_dead_task(task)
    proposal=BidProposal.objects.filter(saved_bid=saved).select_related('saved_bid__bid_notice').first() if not task or task.status not in {'queued','running'} else None
    from .views import serialize_bid_proposal
    return Response({'task':task_data(task) if task else None,
                     'proposal':serialize_bid_proposal(proposal) if proposal else None})
