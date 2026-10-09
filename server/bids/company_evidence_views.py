"""Owner-scoped company evidence review; approval never calls a model."""
from pathlib import Path
from datetime import timedelta
import requests

from django.core.paginator import Paginator
from django.http import FileResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CompanyDocument, CompanyKnowledgeItem
from .serializers import CompanyEvidenceReviewSerializer
from .services.company_evidence import evidence_fingerprint, effective_review_status, serialize_evidence


def owner_items(user):
    return CompanyKnowledgeItem.objects.filter(user=user).select_related(
        'source_document', 'source_website_page', 'reviewed_by').order_by('category', 'id')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def evidence_list(request):
    wanted = request.query_params.get('status', '')
    if wanted not in {'', 'pending', 'approved', 'excluded', 'expired', 'changed'}:
        return Response({'error':'검토 상태를 확인해 주세요.'}, status=400)
    category = request.query_params.get('category', '')
    if category and category not in CompanyKnowledgeItem.Category.values:
        return Response({'error':'자료 분류를 확인해 주세요.'}, status=400)
    cache, counts, items = {}, {}, []
    for item in owner_items(request.user):
        state = effective_review_status(item, cache)
        counts[state] = counts.get(state, 0) + 1
        if (not wanted or state == wanted) and (not category or item.category == category):
            items.append(item)
    page = Paginator(items, 20).get_page(request.query_params.get('page', 1))
    return Response({'count':len(items), 'counts':counts, 'page':page.number,
        'pages':page.paginator.num_pages, 'items':[serialize_evidence(item, cache) for item in page],
        'categories':[{'value':value,'label':label} for value,label in CompanyKnowledgeItem.Category.choices]})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def evidence_review(request, item_id):
    item = owner_items(request.user).filter(pk=item_id).first()
    if item is None:
        return Response({'error':'회사 근거 항목을 찾을 수 없습니다.'}, status=404)
    serializer = CompanyEvidenceReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    expected = data.pop('expected_updated_at')
    confirmed = data.pop('confirm_source_review')
    if item.updated_at != expected:
        return Response({'error':'항목이 변경되었습니다. 목록을 새로 불러온 뒤 검토해 주세요.'}, status=409)
    for key,value in data.items():
        setattr(item, key, value)
    now = max(timezone.now(), item.updated_at + timedelta(microseconds=1))
    fingerprint = ''
    if item.review_status == 'approved':
        if not confirmed:
            return Response({'error':'원문과 발췌 내용을 확인한 뒤 검토 완료로 저장해 주세요.'}, status=400)
        if item.valid_until and item.valid_until < timezone.localdate():
            return Response({'error':'유효기간이 지난 근거는 검토 완료로 저장할 수 없습니다.'}, status=400)
        if not item.evidence_excerpt.strip() or not any(str(value).strip() for value in item.source_locations):
            return Response({'error':'출처 위치와 원문 발췌가 필요합니다. 자료를 다시 분석해 주세요.'}, status=400)
        fingerprint = evidence_fingerprint(item)
        if not fingerprint:
            return Response({'error':'원문을 읽지 못했습니다. 본인의 출처 자료를 확인해 주세요.'}, status=400)
    data.update(reviewed_by=request.user if item.review_status != 'pending' else None,
        reviewed_at=now if item.review_status != 'pending' else None, review_fingerprint=fingerprint,
        updated_at=now)
    if not CompanyKnowledgeItem.objects.filter(pk=item.pk,user=request.user,updated_at=expected).update(**data):
        return Response({'error':'저장 중 항목이 변경되었습니다. 다시 불러와 주세요.'}, status=409)
    item.refresh_from_db()
    return Response({'item':serialize_evidence(item)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_knowledge(request, document_id):
    document = CompanyDocument.objects.filter(user=request.user, pk=document_id).first()
    if document is None:
        return Response({'error':'회사 문서를 찾을 수 없습니다.'}, status=404)
    from .services.company_knowledge import prepare_company_knowledge
    try:
        result = prepare_company_knowledge(document, force=request.data.get('force') is True)
    except (OSError, ValueError, requests.RequestException):
        return Response({'error':'회사 근거를 추출하지 못했습니다. 문서의 텍스트와 모델 연결을 확인해 주세요.'}, status=502)
    return Response({'item_count':result['item_count'], 'reused':result['reused']})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_download(request, document_id):
    document = CompanyDocument.objects.filter(user=request.user, pk=document_id).first()
    if document is None:
        return Response({'error':'회사 문서를 찾을 수 없습니다.'}, status=404)
    try:
        return FileResponse(document.file.open('rb'), as_attachment=True,
            filename=Path(document.original_name).name)
    except OSError:
        return Response({'error':'원문 파일을 읽지 못했습니다.'}, status=404)
