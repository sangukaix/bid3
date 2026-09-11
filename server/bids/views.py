from datetime import timedelta
from io import StringIO
from pathlib import Path
import logging
import re
import time

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.paginator import EmptyPage, Paginator
from django.db import OperationalError
from django.db.models import Count, F, Max, Q
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import BidAnalysis, BidChatMessage, BidNotice, BidProposal, BidQuantitativeProposal, CompanyDocument, CompanyProfile, ProjectReferenceDocument, RecommendedBid, SavedBid
from .serializers import CompanyDocumentSerializer, CompanyProfileSerializer, LoginSerializer, ProjectReferenceDocumentSerializer, SignupSerializer
from .services.business_registration import extract_business_registration
from .services.proposal_template_recommendation import recommend_proposal_template
from .services.recommendation import get_profile_keywords


logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
RECOMMENDATION_LIMIT = 20
MAX_CHAT_QUESTION_LENGTH = 500  # 지나치게 긴 질문과 AI 비용을 제한
PROPOSAL_REVISION_HINTS = (
    "수정해",
    "수정해줘",
    "바꿔",
    "변경해",
    "추가해",
    "삭제해",
    "넣어줘",
    "작성해",
    "만들어",
    "반영해",
)
PREFERRED_BID_TYPE_MAP = {
    "service": "용역",
    "goods": "물품",
    "construction": "공사",
}
BUSINESS_TYPES = {"물품", "용역", "공사"}
DEADLINE_STATUSES = {
    BidNotice.DeadlineStatus.ACTIVE,
    BidNotice.DeadlineStatus.REVIEW,
}
REGIONS = {
    "seoul": "서울",
    "busan": "부산",
    "daegu": "대구",
    "incheon": "인천",
    "gwangju": "광주",
    "daejeon": "대전",
    "ulsan": "울산",
    "sejong": "세종",
    "gyeonggi": "경기",
    "gangwon": "강원",
    "chungbuk": "충북",
    "chungnam": "충남",
    "jeonbuk": "전북",
    "jeonnam": "전남",
    "gyeongbuk": "경북",
    "gyeongnam": "경남",
    "jeju": "제주",
}


def save_with_sqlite_retry(instance, attempts=3):
    """로컬 SQLite가 잠시 사용 중이면 AI 결과 저장을 짧게 재시도합니다."""

    for attempt in range(attempts):
        try:
            instance.save()
            return
        except OperationalError as error:
            is_locked = "database is locked" in str(error).lower()
            if not is_locked or attempt == attempts - 1:
                raise
            time.sleep(attempt + 1)


DEADLINE_DAYS = {0, 3, 7, 30}
DEADLINE_SORTS = {"asc", "desc"}
NOTICE_SORTS = {"asc", "desc"}
CONTRACT_METHODS = {"제한경쟁", "수의계약", "일반경쟁"}
REGION_ALIASES = {
    "충북": ("충북", "충청북도"),
    "충남": ("충남", "충청남도"),
    "전북": ("전북", "전라북도"),
    "전남": ("전남", "전라남도"),
    "경북": ("경북", "경상북도"),
    "경남": ("경남", "경상남도"),
}


def build_region_condition(regions):
    condition = Q(region_limit=False)  # 지역 제한이 없으면 어느 희망 지역에서든 참가 가능

    for region in regions:
        for alias in REGION_ALIASES.get(region, (region,)):
            condition |= Q(allowed_region__icontains=alias)

    return condition


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()  # 현재 사용자의 로그인 Token 삭제
    return Response({"message": "로그아웃되었습니다."})


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)  # 사용자 인증표 발급
        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            }
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()  # 검사된 정보로 Django 회원 생성
        return Response(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                }
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST", "PATCH"])
@permission_classes([IsAuthenticated])
def company_profile(request):
    profile = CompanyProfile.objects.filter(user=request.user).first()

    if request.method == "GET":  # 로그인한 사용자의 회사 정보 조회
        if profile is None:
            return Response({"profile": None})

        serializer = CompanyProfileSerializer(profile)
        return Response({"profile": serializer.data})

    if request.method == "PATCH":  # 기존 회사 정보 중 전달받은 값만 수정
        if profile is None:
            return Response(
                {"error": "Company profile does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompanyProfileSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"profile": serializer.data})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if profile is not None:  # 한 사용자에게 회사 프로필이 중복 저장되는 것을 방지
        return Response(
            {"error": "Company profile already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = CompanyProfileSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)  # 로그인한 사용자를 회사 프로필에 연결
        return Response(
            {"profile": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def company_document_list(request):
    documents = CompanyDocument.objects.filter(user=request.user)

    if request.method == "GET":
        serializer = CompanyDocumentSerializer(
            documents,
            many=True,
            context={"request": request},
        )
        return Response({"count": documents.count(), "items": serializer.data})

    if documents.count() >= 10:
        return Response(
            {"error": "회사 문서는 최대 10개까지 업로드할 수 있습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = CompanyDocumentSerializer(
        data=request.data,
        context={"request": request},
    )
    if serializer.is_valid():
        uploaded_file = serializer.validated_data["file"]
        document = serializer.save(
            user=request.user,
            original_name=uploaded_file.name,
        )
        response_serializer = CompanyDocumentSerializer(
            document,
            context={"request": request},
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def company_document_delete(request, document_id):
    document = CompanyDocument.objects.filter(
        id=document_id,
        user=request.user,
    ).first()
    if document is None:
        return Response(
            {"error": "삭제할 회사 문서를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    document.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def company_website_knowledge(request):
    """회사 홈페이지 수집 상태를 조회하거나 사용자가 직접 새로 수집합니다."""

    from .services.company_knowledge import prepare_website_knowledge
    from .services.company_website import collect_company_websites

    collection = None
    if request.method == "POST":
        try:
            collection = collect_company_websites(request.user, force=True)
            for page in request.user.company_website_pages.all():
                prepare_website_knowledge(page)
        except (OSError, ValueError) as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    pages = request.user.company_website_pages.prefetch_related(
        "knowledge_items"
    )
    return Response(
        {
            "count": pages.count(),
            "items": [
                {
                    "id": page.id,
                    "url": page.url,
                    "title": page.title,
                    "knowledge_count": len(page.knowledge_items.all()),
                    "collected_at": page.collected_at,
                }
                for page in pages
            ],
            "collection": collection,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def business_registration_extract(request):
    """사업자등록증에 실제 적힌 회사 기본정보만 추출합니다."""

    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return Response(
            {"error": "사업자등록증 파일을 선택해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        return Response(extract_business_registration(uploaded_file))
    except ValueError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"error": "사업자등록증을 분석하지 못했습니다. 파일 상태를 확인해 주세요."},
            status=status.HTTP_502_BAD_GATEWAY,
        )


def parse_positive_integer(value, default, name):
    if value is None:
        return default

    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a positive integer.") from error

    if number < 1:
        raise ValueError(f"{name} must be a positive integer.")

    return number


def get_last_updated_at():
    return BidNotice.objects.aggregate(last_updated_at=Max("updated_at"))[
        "last_updated_at"
    ]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_bid_notices(request):
    """나라장터 최근 30일 공고를 즉시 다시 수집합니다."""
    command_output = StringIO()  # 관리 명령의 긴 터미널 출력을 API 응답에서 숨김

    try:
        call_command("sync_bids", stdout=command_output)
    except Exception:
        return Response(
            {"error": "나라장터 공고 업데이트에 실패했습니다."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(
        {
            "message": "입찰공고를 최신 정보로 업데이트했습니다.",
            "last_updated_at": get_last_updated_at(),
            "count": BidNotice.objects.count(),
        }
    )


def serialize_notice(notice, match_reasons=None):
    item = dict(notice.raw_data or {})
    item["deadlineStatus"] = notice.deadline_status
    item["isActive"] = notice.is_active
    item["regionLimit"] = notice.region_limit
    item["allowedRegion"] = notice.allowed_region or "전국"
    item["bidNtceUrl"] = item.get("bidNtceUrl") or notice.source_url
    item["ntceInsttNm"] = item.get("ntceInsttNm") or notice.notice_organization
    item["dminsttNm"] = item.get("dminsttNm") or notice.demand_organization
    item["cntrctCnclsMthdNm"] = item.get("cntrctCnclsMthdNm") or notice.contract_method

    if match_reasons is not None:
        item["matchReasons"] = match_reasons

    return item


CURRENT_PROPOSAL_VERSION = "template_generation_v1"


def is_current_proposal(proposal):
    """현재 Bid2 템플릿 방식으로 생성한 제안서인지 확인합니다."""

    return bool(
        proposal
        and (proposal.revision_plan or {}).get("version")
        == CURRENT_PROPOSAL_VERSION
    )


def serialize_saved_bid(saved_bid):
    item = serialize_notice(saved_bid.bid_notice)  # 연결된 입찰공고를 JSON 형태로 변환
    item["savedAt"] = saved_bid.created_at
    item["hasChat"] = bool(saved_bid.chat_messages.all())
    item["hasAnalysis"] = hasattr(saved_bid, "analysis")
    item["hasProposal"] = is_current_proposal(
        getattr(saved_bid, "proposal", None)
    )
    project_exists = bool(saved_bid.proposal_started_at or item["hasProposal"])
    item["hasProposalProject"] = bool(
        project_exists and saved_bid.proposal_trashed_at is None
    )
    item["isProposalTrashed"] = saved_bid.proposal_trashed_at is not None
    item["proposalProjectStartedAt"] = saved_bid.proposal_started_at
    item["proposalTrashedAt"] = saved_bid.proposal_trashed_at
    return item


def serialize_recommendation(recommendation):
    item = serialize_notice(
        recommendation.bid_notice,
        recommendation.match_reasons,
    )
    item["matchScore"] = recommendation.match_score
    item["matchedKeywords"] = recommendation.matched_keywords
    item["matchedAt"] = recommendation.created_at
    item["notificationSentAt"] = recommendation.notification_sent_at
    return item


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stored_recommendation_list(request):
    recommendations = RecommendedBid.objects.filter(
        user=request.user,
        bid_notice__is_active=True,
        is_match=True,
    ).exclude(
        bid_notice__deadline_status=BidNotice.DeadlineStatus.EXPIRED,
    ).filter(
        Q(bid_notice__close_at__isnull=True)
        | Q(bid_notice__close_at__gte=timezone.now())
    ).select_related("bid_notice").order_by(
        "-match_score",
        "-title_match_count",
        "-bid_notice__notice_date",
        "-bid_notice__close_at",
    )
    return Response(
        {
            "count": recommendations.count(),
            "pending_notification_count": recommendations.filter(
                notification_sent_at__isnull=True,
            ).count(),
            "items": [
                serialize_recommendation(recommendation)
                for recommendation in recommendations[:100]
            ],
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def saved_bid_list(request):
    if request.method == "GET":
        saved_bids = SavedBid.objects.filter(user=request.user).select_related(
            "bid_notice", "analysis", "proposal"
        ).prefetch_related("chat_messages")  # 사용 여부까지 한 번에 조회
        return Response(
            {
                "count": saved_bids.count(),
                "items": [serialize_saved_bid(saved_bid) for saved_bid in saved_bids],
            }
        )

    bid_ntce_no = str(request.data.get("bid_ntce_no", "")).strip()
    if not bid_ntce_no:
        return Response(
            {"error": "공고번호를 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    notice = (
        BidNotice.objects.filter(
            bid_ntce_no=bid_ntce_no,
            is_active=True,
        )
        .order_by("-bid_ntce_ord")
        .first()
    )  # 공고번호와 일치하는 최신 활성 공고 조회
    if notice is None:
        return Response(
            {"error": "저장할 입찰공고를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    saved_bid = SavedBid.objects.filter(
        user=request.user,
        bid_notice__bid_ntce_no=bid_ntce_no,
    ).first()
    if saved_bid is not None:
        if saved_bid.bid_notice_id != notice.id:
            saved_bid.bid_notice = notice
            saved_bid.save(update_fields=["bid_notice"])
        return Response(
            {"created": False, "item": serialize_saved_bid(saved_bid)}
        )  # 이미 저장한 공고면 중복 생성 없이 기존 저장 결과 반환

    saved_bid = SavedBid.objects.create(
        user=request.user,
        bid_notice=notice,
    )  # 로그인한 회원과 선택한 공고를 SavedBid로 연결
    return Response(
        {"created": True, "item": serialize_saved_bid(saved_bid)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def saved_bid_delete(request, bid_ntce_no):
    saved_bid = SavedBid.objects.filter(
        user=request.user,
        bid_notice__bid_ntce_no=bid_ntce_no,
    ).first()

    if saved_bid is None:
        return Response(
            {"error": "저장한 입찰공고를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if saved_bid.proposal_started_at or hasattr(saved_bid, "proposal"):
        return Response(
            {"error": "진행 중인 제안서 프로젝트가 있어 저장을 취소할 수 없습니다. 프로젝트를 먼저 삭제해 주세요."},
            status=status.HTTP_409_CONFLICT,
        )

    saved_bid.delete()  # 프로젝트가 없는 저장 공고만 취소
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def start_bid_proposal_project(request, bid_ntce_no):
    """제안서 화면을 연 공고를 사용자별 프로젝트로 기록합니다."""

    saved_bid = SavedBid.objects.filter(
        user=request.user,
        bid_notice__bid_ntce_no=bid_ntce_no,
    ).select_related("bid_notice").first()
    if saved_bid is None:
        return Response(
            {"error": "저장한 입찰공고를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        if saved_bid.proposal_started_at is None and not hasattr(saved_bid, "proposal"):
            return Response(
                {"error": "이동할 제안서 프로젝트가 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        saved_bid.proposal_trashed_at = timezone.now()
        saved_bid.save(update_fields=["proposal_trashed_at"])
        return Response(serialize_saved_bid(saved_bid))

    if saved_bid.proposal_trashed_at is not None:
        return Response(
            {"error": "휴지통에 있는 프로젝트입니다. 휴지통에서 복원해 주세요."},
            status=status.HTTP_409_CONFLICT,
        )

    if saved_bid.proposal_started_at is None:
        saved_bid.proposal_started_at = timezone.now()
        saved_bid.save(update_fields=["proposal_started_at"])

    return Response(serialize_saved_bid(saved_bid))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def proposal_trash_list(request):
    """삭제 대신 보관 중인 제안서 프로젝트를 조회합니다."""

    saved_bids = (
        SavedBid.objects.filter(
            user=request.user,
            proposal_trashed_at__isnull=False,
        )
        .select_related("bid_notice", "analysis", "proposal")
        .prefetch_related("chat_messages")
        .order_by("-proposal_trashed_at")
    )
    return Response(
        {
            "count": saved_bids.count(),
            "items": [serialize_saved_bid(saved_bid) for saved_bid in saved_bids],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def restore_bid_proposal_project(request, bid_ntce_no):
    """휴지통 프로젝트를 마지막 프로젝트 순서로 복원합니다."""

    saved_bid = SavedBid.objects.filter(
        user=request.user,
        bid_notice__bid_ntce_no=bid_ntce_no,
        proposal_trashed_at__isnull=False,
    ).select_related("bid_notice").first()
    if saved_bid is None:
        return Response(
            {"error": "복원할 프로젝트를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )
    saved_bid.proposal_trashed_at = None
    saved_bid.proposal_started_at = timezone.now()
    saved_bid.save(
        update_fields=["proposal_trashed_at", "proposal_started_at"]
    )
    return Response(serialize_saved_bid(saved_bid))


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def permanently_delete_bid_proposal_project(request, bid_ntce_no):
    """휴지통의 제안서 작업 데이터만 복구 불가능하게 삭제합니다."""

    saved_bid = SavedBid.objects.filter(
        user=request.user,
        bid_notice__bid_ntce_no=bid_ntce_no,
        proposal_trashed_at__isnull=False,
    ).first()
    if saved_bid is None:
        return Response(
            {"error": "영구 삭제할 프로젝트를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    for document in saved_bid.reference_documents.all():
        document.delete()
    BidProposal.objects.filter(saved_bid=saved_bid).delete()
    BidAnalysis.objects.filter(saved_bid=saved_bid).delete()
    BidQuantitativeProposal.objects.filter(saved_bid=saved_bid).delete()
    saved_bid.chat_messages.all().delete()
    saved_bid.proposal_started_at = None
    saved_bid.proposal_trashed_at = None
    saved_bid.save(
        update_fields=["proposal_started_at", "proposal_trashed_at"]
    )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def project_reference_document_list(request, bid_ntce_no):
    """현재 제안서 프로젝트에서만 사용할 유사 제안서를 관리합니다."""

    saved_bid = SavedBid.objects.filter(
        user=request.user,
        bid_notice__bid_ntce_no=bid_ntce_no,
        proposal_trashed_at__isnull=True,
    ).select_related("bid_notice").first()
    if saved_bid is None:
        return Response(
            {"error": "제안서 프로젝트를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    documents = saved_bid.reference_documents.all()
    if request.method == "GET":
        serializer = ProjectReferenceDocumentSerializer(documents, many=True)
        return Response({"count": documents.count(), "items": serializer.data})

    if documents.count() >= 3:
        return Response(
            {"error": "프로젝트 유사 제안서는 최대 3개까지 등록할 수 있습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = ProjectReferenceDocumentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    uploaded_file = serializer.validated_data["file"]
    document = serializer.save(
        saved_bid=saved_bid,
        original_name=uploaded_file.name,
    )
    return Response(
        ProjectReferenceDocumentSerializer(document).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def project_reference_document_delete(request, bid_ntce_no, document_id):
    """현재 사용자의 프로젝트 참고 제안서만 삭제합니다."""

    document = ProjectReferenceDocument.objects.filter(
        id=document_id,
        saved_bid__user=request.user,
        saved_bid__bid_notice__bid_ntce_no=bid_ntce_no,
    ).first()
    if document is None:
        return Response(
            {"error": "삭제할 유사 제안서를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )
    document.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def build_match_reasons(
    notice,
    keywords,
    preferred_business_type,
    preferred_regions,
    profile,
):
    searchable_text = " ".join(
        [
            notice.title,
            notice.allowed_industry,
            notice.notice_organization,
            notice.demand_organization,
        ]
    ).lower()
    matched_keywords = [
        keyword for keyword in keywords if keyword.lower() in searchable_text
    ]
    reasons = [f"키워드 일치: {', '.join(matched_keywords)}"]

    if preferred_business_type:
        reasons.append(f"업무 구분 일치: {preferred_business_type}")

    if preferred_regions:
        reasons.append("전국 참가 가능" if not notice.region_limit else "희망 지역 일치")

    return reasons


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommended_bid_list(request):
    profile = CompanyProfile.objects.filter(user=request.user).first()  # 현재 사용자의 회사 정보

    if "keywords" in request.GET:
        keyword_text = request.GET.get("keywords", "")  # 추천 화면에서 보낸 임시 키워드
    else:
        keyword_text = ",".join(get_profile_keywords(profile)) if profile else ""  # 저장된 회사 키워드

    if "region" in request.GET:
        region_text = request.GET.get("region", "")  # 추천 화면에서 임시로 바꾼 지역
    else:
        region_text = profile.preferred_region if profile else ""  # 저장된 회사 희망 지역

    keywords = [
        keyword.strip()
        for keyword in keyword_text.split(",")
        if keyword.strip()
    ]  # 쉼표로 연결된 문장을 검색 가능한 키워드 목록으로 변환
    preferred_regions = [
        region.strip()
        for region in region_text.split(",")
        if region.strip()
    ]  # 쉼표로 연결된 희망 지역을 목록으로 변환

    if not keywords:
        last_updated_at = get_last_updated_at()
        return Response(
            {
                "keywords": [],
                "region": ", ".join(preferred_regions),
                "count": 0,
                "last_updated_at": last_updated_at,
                "items": [],
            }
        )

    keyword_condition = Q()
    for keyword in keywords:
        keyword_condition |= (
            Q(title__icontains=keyword)
            | Q(allowed_industry__icontains=keyword)
            | Q(notice_organization__icontains=keyword)
            | Q(demand_organization__icontains=keyword)
        )  # 공고명, 업종, 기관 중 한 곳이라도 키워드가 포함되면 추천

    notices = BidNotice.objects.filter(is_active=True).filter(keyword_condition)
    preferred_business_type = (
        PREFERRED_BID_TYPE_MAP.get(profile.preferred_bid_type)
        if profile
        else None
    )

    if preferred_business_type:
        notices = notices.filter(business_type=preferred_business_type)  # 회사의 희망 공고 유형 적용

    if preferred_regions:
        notices = notices.filter(build_region_condition(preferred_regions))

    notices = notices.order_by("-notice_date", "-id")
    total_count = notices.count()
    recommended_notices = notices[:RECOMMENDATION_LIMIT]
    last_updated_at = get_last_updated_at()

    return Response(
        {
            "keywords": keywords,
            "region": ", ".join(preferred_regions),
            "count": total_count,
            "last_updated_at": last_updated_at,
            "items": [
                serialize_notice(
                    notice,
                    build_match_reasons(
                        notice,
                        keywords,
                        preferred_business_type,
                        preferred_regions,
                        profile,
                    ),
                )
                for notice in recommended_notices
            ],
        }
    )


def filter_notices(notices, request):
    query = request.GET.get("q", "").strip()
    keyword_text = request.GET.get("keywords", "").strip()
    region_text = request.GET.get("regions", "").strip()
    business_type = request.GET.get("business_type", "").strip()
    deadline_status = request.GET.get("deadline_status", "").strip()
    region = request.GET.get("region", "").strip()
    deadline_days = request.GET.get("deadline_days", "").strip()
    contract_method = request.GET.get("contract_method", "").strip()

    if query:
        notices = notices.filter(
            Q(title__icontains=query)
            | Q(bid_ntce_no__icontains=query)
            | Q(notice_organization__icontains=query)
            | Q(demand_organization__icontains=query)
            | Q(allowed_region__icontains=query)
            | Q(allowed_industry__icontains=query)
        )

    keywords = [keyword.strip() for keyword in keyword_text.split(",") if keyword.strip()]
    if keywords:
        keyword_condition = Q()
        for keyword in keywords:
            keyword_condition |= (
                Q(title__icontains=keyword)
                | Q(notice_organization__icontains=keyword)
                | Q(demand_organization__icontains=keyword)
                | Q(allowed_industry__icontains=keyword)
            )
        notices = notices.filter(keyword_condition)  # 회사 키워드 중 하나라도 맞는 공고 검색

    if business_type:
        if business_type not in BUSINESS_TYPES:
            raise ValueError("business_type is not valid.")
        notices = notices.filter(business_type=business_type)

    if contract_method:
        if contract_method not in CONTRACT_METHODS:
            raise ValueError("contract_method is not valid.")
        notices = notices.filter(contract_method__icontains=contract_method)

    if deadline_status:
        if deadline_status not in DEADLINE_STATUSES:
            raise ValueError("deadline_status is not valid.")
        notices = notices.filter(deadline_status=deadline_status)

    if region:
        if region not in REGIONS:
            raise ValueError("region is not valid.")
        notices = notices.filter(build_region_condition([REGIONS[region]]))

    preferred_regions = [
        selected_region.strip()
        for selected_region in region_text.split(",")
        if selected_region.strip()
    ]
    if preferred_regions:
        notices = notices.filter(build_region_condition(preferred_regions))

    if deadline_days:
        try:
            days = int(deadline_days)
        except ValueError as error:
            raise ValueError("deadline_days is not valid.") from error

        if days not in DEADLINE_DAYS:
            raise ValueError("deadline_days is not valid.")

        now = timezone.now()
        if days == 0:
            notices = notices.filter(close_at__date=timezone.localdate())
        else:
            notices = notices.filter(
                close_at__gte=now,
                close_at__lte=now + timedelta(days=days),
            )

    return notices


def bid_list(request):
    try:
        page_number = parse_positive_integer(request.GET.get("page"), 1, "page")
        page_size = parse_positive_integer(
            request.GET.get("page_size"),
            DEFAULT_PAGE_SIZE,
            "page_size",
        )
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)

    if page_size > MAX_PAGE_SIZE:
        return JsonResponse(
            {"error": f"page_size cannot be greater than {MAX_PAGE_SIZE}."},
            status=400,
        )

    deadline_sort = request.GET.get("deadline_sort", "").strip()
    if deadline_sort and deadline_sort not in DEADLINE_SORTS:
        return JsonResponse({"error": "deadline_sort is not valid."}, status=400)
    notice_sort = request.GET.get("notice_sort", "").strip()
    if notice_sort and notice_sort not in NOTICE_SORTS:
        return JsonResponse({"error": "notice_sort is not valid."}, status=400)

    notices = BidNotice.objects.filter(is_active=True)

    try:
        notices = filter_notices(notices, request)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)

    summary = notices.aggregate(
        total=Count("id"),
        goods=Count("id", filter=Q(business_type="물품")),
        services=Count("id", filter=Q(business_type="용역")),
        construction=Count("id", filter=Q(business_type="공사")),
    )
    if notice_sort == "asc":
        notices = notices.order_by(F("notice_date").asc(nulls_last=True), "id")
    elif notice_sort == "desc":
        notices = notices.order_by(F("notice_date").desc(nulls_last=True), "-id")
    elif deadline_sort == "asc":
        notices = notices.order_by(F("close_at").asc(nulls_last=True), "-id")
    elif deadline_sort == "desc":
        notices = notices.order_by(F("close_at").desc(nulls_last=True), "-id")
    else:
        notices = notices.order_by("-notice_date", "-id")
    paginator = Paginator(notices, page_size)

    try:
        page = paginator.page(page_number)
    except EmptyPage:
        return JsonResponse({"error": "The requested page does not exist."}, status=404)

    return JsonResponse(
        {
            "count": paginator.count,
            "page": page.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "last_updated_at": get_last_updated_at(),
            "summary": summary,
            "items": [serialize_notice(notice) for notice in page.object_list],
        }
    )


def bid_detail(request, bid_ntce_no):  # URL로 받은 공고번호의 상세정보를 조회
    notice = (
        BidNotice.objects.filter(
            bid_ntce_no=bid_ntce_no,
            is_active=True,
        )
        .order_by("-bid_ntce_ord")
        .first()
    )  # 같은 공고번호가 여러 차수면 가장 최신 활성 공고 한 건 선택

    if notice is None:
        return JsonResponse(
            {"error": "입찰공고를 찾을 수 없습니다."},
            status=404,
        )  # 없는 공고번호임을 HTTP 404로 전달

    return JsonResponse(
        {"item": serialize_notice(notice)}
    )  # DB 공고를 브라우저가 사용할 JSON 형태로 전달


def generate_bid_chat_answer(bid_ntce_no, question):
    """필요할 때만 RAG 챗봇 모듈을 불러와 답변을 생성합니다."""
    from .services.rag.chatbot import ask_bid_question

    return ask_bid_question(bid_ntce_no, question)


def serialize_chat_message(message):
    """DB 대화 한 건을 삭제 상태까지 포함해 화면용 JSON으로 만듭니다."""

    return {
        "id": message.id,
        "role": message.role,
        "text": (
            "삭제된 메시지입니다."
            if message.is_deleted
            else message.content
        ),
        "sources": [] if message.is_deleted else message.sources,
        "messageType": message.message_type,
        "status": message.status,
        "isDeleted": message.is_deleted,
        "createdAt": message.created_at,
    }


def detect_assistant_intent(message, has_proposal, requested_intent="auto"):
    """한 대화창의 입력을 공고 질문 또는 제안서 수정 요청으로 분류합니다."""

    if requested_intent in {"question", "revision"}:
        return requested_intent
    if has_proposal and any(
        keyword in message for keyword in PROPOSAL_REVISION_HINTS
    ):
        return "revision"
    return "question"


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bid_chat(request, bid_ntce_no):
    """공고 질문과 제안서 수정 요청을 하나의 대화 기록으로 관리합니다."""
    notice = (
        BidNotice.objects.filter(bid_ntce_no=bid_ntce_no, is_active=True)
        .order_by("-bid_ntce_ord")
        .first()
    )
    if notice is None:
        return Response(
            {"error": "입찰공고를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    saved_bid, _ = SavedBid.objects.get_or_create(
        user=request.user,
        bid_notice=notice,
    )  # 채팅 기록을 회원과 공고별로 저장할 기준

    if request.method == "GET":
        return Response(
            {
                "messages": [
                    serialize_chat_message(message)
                    for message in saved_bid.chat_messages.all()
                ],
                "pendingRevisionCount": saved_bid.chat_messages.filter(
                    role=BidChatMessage.Role.USER,
                    message_type=BidChatMessage.MessageType.PROPOSAL,
                    status=BidChatMessage.Status.PENDING,
                    is_deleted=False,
                ).count(),
            }
        )

    question = request.data.get("message", request.data.get("question"))

    if not isinstance(question, str) or not question.strip():
        return Response(
            {"error": "질문을 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    question = question.strip()
    if len(question) > 1000:
        return Response(
            {"error": "메시지는 1,000자 이하로 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    proposal = getattr(saved_bid, "proposal", None)
    intent = detect_assistant_intent(
        question,
        is_current_proposal(proposal),
        str(request.data.get("intent", "auto")),
    )
    if intent == "revision":
        if not is_current_proposal(proposal):
            return Response(
                {"error": "먼저 제안서 초안을 만들어 주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        requested_slide_counts = [
            int(value)
            for value in re.findall(r"(\d{2,3})\s*(?:장|페이지|슬라이드)", question)
        ]
        if any(count > 50 for count in requested_slide_counts):
            user_message = BidChatMessage.objects.create(
                saved_bid=saved_bid,
                role=BidChatMessage.Role.USER,
                message_type=BidChatMessage.MessageType.PROPOSAL,
                status=BidChatMessage.Status.APPLIED,
                content=question,
            )
            assistant_message = BidChatMessage.objects.create(
                saved_bid=saved_bid,
                role=BidChatMessage.Role.ASSISTANT,
                message_type=BidChatMessage.MessageType.PROPOSAL,
                status=BidChatMessage.Status.APPLIED,
                content="현재 제안서는 최대 50장까지만 제작할 수 있습니다. 50장 이내의 구성으로 요청해 주세요.",
            )
            return Response(
                {
                    "intent": "revision",
                    "messages": [
                        serialize_chat_message(user_message),
                        serialize_chat_message(assistant_message),
                    ],
                    "pendingRevisionCount": 0,
                }
            )
        if any(keyword in question for keyword in ("그래프", "차트", "사진", "이미지")):
            user_message = BidChatMessage.objects.create(
                saved_bid=saved_bid,
                role=BidChatMessage.Role.USER,
                message_type=BidChatMessage.MessageType.PROPOSAL,
                status=BidChatMessage.Status.APPLIED,
                content=question,
            )
            assistant_message = BidChatMessage.objects.create(
                saved_bid=saved_bid,
                role=BidChatMessage.Role.ASSISTANT,
                message_type=BidChatMessage.MessageType.PROPOSAL,
                status=BidChatMessage.Status.APPLIED,
                content=(
                    "웹에서 출처가 확인된 자료를 찾아 문구와 수치로 반영할 수 있습니다. "
                    "다만 현재 버전은 그래프나 외부 이미지를 슬라이드에 자동 삽입하지 못합니다. "
                    "필요하면 ‘웹 검색한 수치를 출처와 함께 텍스트 슬라이드로 추가해줘’라고 요청해 주세요."
                ),
            )
            return Response(
                {
                    "intent": "revision",
                    "messages": [
                        serialize_chat_message(user_message),
                        serialize_chat_message(assistant_message),
                    ],
                    "pendingRevisionCount": 0,
                }
            )
        message = BidChatMessage.objects.create(
            saved_bid=saved_bid,
            role=BidChatMessage.Role.USER,
            message_type=BidChatMessage.MessageType.PROPOSAL,
            status=BidChatMessage.Status.PENDING,
            content=question,
            sources=[
                {"slide_number": request.data.get("slide_number")}
            ],
        )
        assistant_message = BidChatMessage.objects.create(
            saved_bid=saved_bid,
            role=BidChatMessage.Role.ASSISTANT,
            message_type=BidChatMessage.MessageType.PROPOSAL,
            status=BidChatMessage.Status.APPLIED,
            content="가능합니다. 요청하신 내용을 제안서에 반영할까요?",
        )
        return Response(
            {
                "intent": "revision",
                "messages": [
                    serialize_chat_message(message),
                    serialize_chat_message(assistant_message),
                ],
                "pendingRevisionCount": saved_bid.chat_messages.filter(
                    role=BidChatMessage.Role.USER,
                    message_type=BidChatMessage.MessageType.PROPOSAL,
                    status=BidChatMessage.Status.PENDING,
                    is_deleted=False,
                ).count(),
            },
            status=status.HTTP_201_CREATED,
        )

    if len(question) > MAX_CHAT_QUESTION_LENGTH:
        return Response(
            {"error": f"공고 질문은 {MAX_CHAT_QUESTION_LENGTH}자 이하로 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = generate_bid_chat_answer(bid_ntce_no, question)
    except ValueError as error:
        return Response(
            {"error": str(error)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        return Response(
            {"error": "AI 답변을 생성하지 못했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    user_message = BidChatMessage.objects.create(
        saved_bid=saved_bid,
        role=BidChatMessage.Role.USER,
        message_type=BidChatMessage.MessageType.QUESTION,
        content=question,
    )
    assistant_message = BidChatMessage.objects.create(
        saved_bid=saved_bid,
        role=BidChatMessage.Role.ASSISTANT,
        message_type=BidChatMessage.MessageType.QUESTION,
        content=result["answer"],
        sources=result.get("sources", []),
    )  # 답변 생성에 성공한 대화만 DB에 저장

    return Response(
        {
            **result,
            "intent": "question",
            "messages": [
                serialize_chat_message(user_message),
                serialize_chat_message(assistant_message),
            ],
        }
    )  # answer와 sources를 Next.js에 전달


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def bid_chat_message_delete(request, bid_ntce_no, message_id):
    """대화 위치는 유지하고 내용만 삭제 표시로 바꿉니다."""

    message = BidChatMessage.objects.filter(
        id=message_id,
        saved_bid__user=request.user,
        saved_bid__bid_notice__bid_ntce_no=bid_ntce_no,
    ).first()
    if message is None:
        return Response(
            {"error": "삭제할 메시지를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    message.content = ""
    message.sources = []
    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.save(
        update_fields=["content", "sources", "is_deleted", "deleted_at"]
    )
    return Response({"message": serialize_chat_message(message)})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bid_analysis(request, bid_ntce_no):
    saved_bid = (
        SavedBid.objects.filter(
            user=request.user,
            bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("bid_notice")
        .first()
    )
    if saved_bid is None:
        return Response(
            {"error": "먼저 공고를 저장해 주세요."},
            status=status.HTTP_404_NOT_FOUND,
        )

    analysis = BidAnalysis.objects.filter(saved_bid=saved_bid).first()
    if request.method == "GET":
        return Response(
            {
                "report": analysis.report if analysis else None,
                "updated_at": analysis.updated_at if analysis else None,
            }
        )

    if analysis is not None:
        return Response(
            {"report": analysis.report, "updated_at": analysis.updated_at}
        )  # 기존 분석은 재사용해 중복 OpenAI 비용 방지

    profile = CompanyProfile.objects.filter(user=request.user).first()
    if profile is None:
        return Response(
            {"error": "AI 분석 전에 회사 정보를 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from .services.rag.analysis import generate_bid_analysis

        report = generate_bid_analysis(bid_ntce_no, profile)
    except ValueError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"error": "AI 분석 리포트를 생성하지 못했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    analysis = BidAnalysis.objects.create(saved_bid=saved_bid, report=report)
    return Response(
        {"report": analysis.report, "updated_at": analysis.updated_at},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bid_analysis_pdf(request, bid_ntce_no):
    analysis = (
        BidAnalysis.objects.filter(
            saved_bid__user=request.user,
            saved_bid__bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("saved_bid__bid_notice", "saved_bid__user")
        .first()
    )
    if analysis is None:
        return Response(
            {"error": "저장된 AI 분석 결과가 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    from .services.analysis_pdf import build_analysis_pdf

    pdf_buffer = build_analysis_pdf(analysis)
    return FileResponse(
        pdf_buffer,
        as_attachment=True,
        filename=f"bid-analysis-{bid_ntce_no}.pdf",
        content_type="application/pdf",
    )


def serialize_bid_proposal(proposal):
    revision_plan = proposal.revision_plan or {}
    proposal_status = revision_plan.get("status", "final")
    return {
        "id": proposal.id,
        "status": proposal_status,
        "output_format": proposal.output_format,
        "template_mode": proposal.template_mode,
        "strategy": proposal.strategy,
        "revision_plan": revision_plan,
        "created_at": proposal.created_at,
        "updated_at": proposal.updated_at,
        "preview_url": (
            f"/api/bids/{proposal.saved_bid.bid_notice.bid_ntce_no}/proposal/preview/"
        ),
        "download_url": (
            f"/api/bids/{proposal.saved_bid.bid_notice.bid_ntce_no}/proposal/download/"
        ),
    }


def serialize_proposal_templates():
    """settings의 허용된 템플릿만 웹에 전달합니다."""

    from pptx import Presentation

    templates = []
    for template_id, template in settings.PROPOSAL_TEMPLATES.items():
        template_path = Path(template["path"])
        slide_count = template["target_slides"]
        if template_path.exists():
            slide_count = len(Presentation(template_path).slides)
        templates.append({
            "id": template_id,
            "name": template["name"],
            "description": template["description"],
            "available": template_path.exists(),
            "target_slides": template["target_slides"],
            "slide_count": slide_count,
            "preview_url": f"/api/proposal-templates/{template_id}/slides/",
        })
    return templates


def serialize_quantitative_proposal(quantitative_proposal):
    """정량평가 저장 결과를 Next.js에서 사용할 형태로 바꿉니다."""

    bid_ntce_no = quantitative_proposal.saved_bid.bid_notice.bid_ntce_no
    return {
        "id": quantitative_proposal.id,
        "report": quantitative_proposal.report,
        "created_at": quantitative_proposal.created_at,
        "updated_at": quantitative_proposal.updated_at,
        "download_url": (
            f"/api/bids/{bid_ntce_no}/quantitative-proposal/download/"
            if quantitative_proposal.generated_file
            else ""
        ),
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bid_quantitative_proposal(request, bid_ntce_no):
    """공고의 정량평가 요구사항을 찾아 작성안을 생성하거나 재조회합니다."""

    saved_bid = (
        SavedBid.objects.filter(
            user=request.user,
            bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("bid_notice")
        .first()
    )
    if saved_bid is None:
        return Response(
            {"error": "먼저 공고를 저장해 주세요."},
            status=status.HTTP_404_NOT_FOUND,
        )

    existing = BidQuantitativeProposal.objects.filter(saved_bid=saved_bid).first()
    if request.method == "GET":
        return Response(
            {
                "quantitative_proposal": (
                    serialize_quantitative_proposal(existing)
                    if existing
                    else None
                )
            }
        )

    regenerate = request.data.get("regenerate") in (True, "true", "1", 1)
    if existing and not regenerate:
        return Response(
            {"quantitative_proposal": serialize_quantitative_proposal(existing)}
        )  # 저장 결과를 재사용해 중복 OpenAI 비용 방지

    profile = CompanyProfile.objects.filter(user=request.user).first()
    if profile is None:
        return Response(
            {"error": "정량평가 작성 전에 회사 정보를 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from .services.quantitative_docx import build_quantitative_docx
        from .services.rag.quantitative import generate_quantitative_proposal

        report = generate_quantitative_proposal(saved_bid, profile)
        file_bytes = build_quantitative_docx(
            saved_bid.bid_notice,
            profile.company_name,
            report,
        )
    except ValueError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("정량평가 자료 생성 실패: %s", bid_ntce_no)
        return Response(
            {"error": "정량평가 자료를 생성하지 못했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    quantitative_proposal = existing or BidQuantitativeProposal(saved_bid=saved_bid)
    previous_file_name = (
        quantitative_proposal.generated_file.name
        if quantitative_proposal.generated_file
        else ""
    )
    quantitative_proposal.report = report
    quantitative_proposal.generated_file.save(
        f"quantitative-{bid_ntce_no}.docx",
        ContentFile(file_bytes),
        save=False,
    )
    save_with_sqlite_retry(quantitative_proposal)
    if previous_file_name and previous_file_name != quantitative_proposal.generated_file.name:
        quantitative_proposal.generated_file.storage.delete(previous_file_name)

    return Response(
        {"quantitative_proposal": serialize_quantitative_proposal(quantitative_proposal)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bid_quantitative_proposal_download(request, bid_ntce_no):
    """저장된 정량평가 Word 작성안을 내려받습니다."""

    quantitative_proposal = (
        BidQuantitativeProposal.objects.filter(
            saved_bid__user=request.user,
            saved_bid__bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("saved_bid__bid_notice")
        .first()
    )
    if quantitative_proposal is None or not quantitative_proposal.generated_file:
        return Response(
            {"error": "내려받을 정량평가 작성안이 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return FileResponse(
        quantitative_proposal.generated_file.open("rb"),
        as_attachment=True,
        filename=f"quantitative-{bid_ntce_no}.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def proposal_template_slide_preview(request, template_id, slide_number):
    """템플릿 선택 화면에 실제 PPT 슬라이드 이미지를 제공합니다."""

    try:
        from .services.proposal_preview import get_template_slide_preview

        image_path, slide_count = get_template_slide_preview(
            template_id,
            slide_number,
        )
    except ValueError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    response = FileResponse(open(image_path, "rb"), content_type="image/png")
    response["X-Slide-Count"] = str(slide_count)
    return response


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bid_proposal(request, bid_ntce_no):
    """저장 공고와 회사 자료를 바탕으로 맞춤 제안서를 생성합니다."""

    saved_bid = (
        SavedBid.objects.filter(
            user=request.user,
            bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("bid_notice", "proposal")
        .first()
    )
    if saved_bid is None:
        return Response(
            {"error": "먼저 공고를 저장해 주세요."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if saved_bid.proposal_trashed_at is not None:
        return Response(
            {"error": "휴지통에 있는 프로젝트입니다. 먼저 복원해 주세요."},
            status=status.HTTP_409_CONFLICT,
        )

    existing_proposal = BidProposal.objects.filter(saved_bid=saved_bid).select_related(
        "saved_bid__bid_notice",
    ).first()

    if request.method == "GET":
        current_proposal = (
            existing_proposal
            if is_current_proposal(existing_proposal)
            else None
        )
        profile = CompanyProfile.objects.filter(user=request.user).first()
        recommendation = recommend_proposal_template(saved_bid.bid_notice, profile)
        if recommendation["id"] not in settings.PROPOSAL_TEMPLATES:
            recommendation = {
                "id": settings.PROPOSAL_DEFAULT_TEMPLATE_ID,
                "reason": "공공입찰의 평가항목과 수행 체계를 안정적으로 구성하는 기본 템플릿입니다.",
                "signals": [],
            }
        selected_template_id = (
            (current_proposal.revision_plan or {}).get("template_id")
            if current_proposal
            else recommendation["id"]
        ) or settings.PROPOSAL_DEFAULT_TEMPLATE_ID
        return Response(
            {
                "item": serialize_notice(saved_bid.bid_notice),
                "proposal": (
                    serialize_bid_proposal(current_proposal)
                    if current_proposal
                    else None
                ),
                "templates": serialize_proposal_templates(),
                "selected_template_id": selected_template_id,
                "recommended_template_id": recommendation["id"],
                "template_recommendation_reason": recommendation["reason"],
            }
        )

    is_current_revision = is_current_proposal(existing_proposal)
    regenerate = request.data.get("regenerate") in (True, "true", "1", 1)
    if is_current_revision and not regenerate:
        return Response(
            {"proposal": serialize_bid_proposal(existing_proposal)}
        )  # 이미 만든 결과를 재사용해 중복 OpenAI 비용 방지

    generation_mode = request.data.get("generation_mode", "default_template")
    if generation_mode != "default_template":
        return Response(
            {"error": "현재는 등록된 제안서 템플릿으로만 생성할 수 있습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    template_id = str(
        request.data.get("template_id", settings.PROPOSAL_DEFAULT_TEMPLATE_ID)
    )
    template = settings.PROPOSAL_TEMPLATES.get(template_id)
    if template is None:
        return Response(
            {"error": "선택한 제안서 템플릿을 찾을 수 없습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not Path(template["path"]).exists():
        return Response(
            {"error": "선택한 제안서 템플릿 파일이 아직 준비되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile = CompanyProfile.objects.filter(user=request.user).first()
    if profile is None:
        return Response(
            {"error": "제안서 생성 전에 회사 정보를 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    previous_revision_plan = (
        dict(existing_proposal.revision_plan or {})
        if existing_proposal
        else None
    )
    if existing_proposal:
        existing_proposal.revision_plan = {
            **previous_revision_plan,
            "status": "generating",
        }
        save_with_sqlite_retry(existing_proposal)

    try:
        from .services.rag.proposal import create_bid_proposal_from_template

        result = create_bid_proposal_from_template(
            saved_bid=saved_bid,
            profile=profile,
            template_path=template["path"],
            target_slide_count=template["target_slides"],
        )
    except ValueError as error:
        if existing_proposal:
            existing_proposal.revision_plan = previous_revision_plan
            save_with_sqlite_retry(existing_proposal)
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("맞춤형 제안서 생성 실패: %s", bid_ntce_no)
        if existing_proposal:
            existing_proposal.revision_plan = previous_revision_plan
            save_with_sqlite_retry(existing_proposal)
        return Response(
            {"error": "맞춤형 제안서를 생성하지 못했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    proposal = existing_proposal or BidProposal(saved_bid=saved_bid)
    previous_file_name = (
        proposal.generated_file.name
        if proposal.generated_file
        else ""
    )
    proposal.output_format = BidProposal.OutputFormat.PPTX
    proposal.template_mode = result["template_mode"]
    proposal.strategy = result["strategy"]
    proposal.revision_plan = {
        **result["revision_plan"],
        "template_id": template_id,
        "template_name": template["name"],
        "status": "draft",
        "feedback_history": [],
    }
    proposal.generated_file.save(
        result["filename"],
        ContentFile(result["file_bytes"]),
        save=False,
    )
    try:
        save_with_sqlite_retry(proposal)
    except Exception:
        proposal.generated_file.delete(save=False)  # DB 저장 실패 시 고아 파일을 남기지 않음
        if existing_proposal:
            proposal.generated_file.name = previous_file_name
            proposal.revision_plan = previous_revision_plan
            save_with_sqlite_retry(proposal)
        return Response(
            {"error": "제안서는 생성됐지만 저장하지 못했습니다. 잠시 후 다시 시도해 주세요."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    from .services.proposal_preview import delete_proposal_preview

    delete_proposal_preview(proposal)
    if previous_file_name and previous_file_name != proposal.generated_file.name:
        proposal.generated_file.storage.delete(previous_file_name)

    return Response(
        {"proposal": serialize_bid_proposal(proposal)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bid_proposal_preview(request, bid_ntce_no):
    """현재 제안서 초안을 PDF로 변환해 브라우저 미리보기에 전달합니다."""

    proposal = (
        BidProposal.objects.filter(
            saved_bid__user=request.user,
            saved_bid__bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("saved_bid__bid_notice", "saved_bid__user")
        .first()
    )
    if proposal is None or not proposal.generated_file:
        return Response(
            {"error": "미리볼 제안서가 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if (proposal.revision_plan or {}).get("status") == "generating":
        return Response(
            {"error": "제안서 생성이 끝난 뒤 수정해 주세요."},
            status=status.HTTP_409_CONFLICT,
        )

    try:
        from .services.proposal_preview import create_proposal_preview

        preview_path = create_proposal_preview(proposal)
    except ValueError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    return FileResponse(
        open(preview_path, "rb"),
        as_attachment=False,
        filename=f"proposal-preview-{bid_ntce_no}.pdf",
        content_type="application/pdf",
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bid_proposal_feedback(request, bid_ntce_no):
    """미리보기 이후 사용자의 요청을 현재 제안서 초안에 반영합니다."""

    proposal = (
        BidProposal.objects.filter(
            saved_bid__user=request.user,
            saved_bid__bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("saved_bid__bid_notice", "saved_bid__user")
        .first()
    )
    if proposal is None or not proposal.generated_file:
        return Response(
            {"error": "먼저 제안서 초안을 만들어 주세요."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if (proposal.revision_plan or {}).get("status") == "generating":
        return Response(
            {"error": "제안서 생성이 끝난 뒤 수정해 주세요."},
            status=status.HTTP_409_CONFLICT,
        )

    direct_instruction = str(request.data.get("instruction", "")).strip()
    direct_slide_number = request.data.get("slide_number")
    confirmation = str(request.data.get("confirmation", "")).strip()
    cancel_requested = request.data.get("cancel") in (True, "true", "1", 1)
    pending_messages = list(
        proposal.saved_bid.chat_messages.filter(
            role=BidChatMessage.Role.USER,
            message_type=BidChatMessage.MessageType.PROPOSAL,
            status=BidChatMessage.Status.PENDING,
            is_deleted=False,
        )
    )
    if direct_instruction:
        direct_message = BidChatMessage.objects.create(
            saved_bid=proposal.saved_bid,
            role=BidChatMessage.Role.USER,
            message_type=BidChatMessage.MessageType.PROPOSAL,
            status=BidChatMessage.Status.PENDING,
            content=direct_instruction,
            sources=[{"slide_number": direct_slide_number}],
        )
        pending_messages.append(direct_message)

    if confirmation:
        BidChatMessage.objects.create(
            saved_bid=proposal.saved_bid,
            role=BidChatMessage.Role.USER,
            message_type=BidChatMessage.MessageType.PROPOSAL,
            status=BidChatMessage.Status.APPLIED,
            content=confirmation,
        )

    if cancel_requested and pending_messages:
        BidChatMessage.objects.filter(
            id__in=[message.id for message in pending_messages]
        ).update(status=BidChatMessage.Status.FAILED)
        assistant_message = BidChatMessage.objects.create(
            saved_bid=proposal.saved_bid,
            role=BidChatMessage.Role.ASSISTANT,
            message_type=BidChatMessage.MessageType.PROPOSAL,
            status=BidChatMessage.Status.APPLIED,
            content="수정 요청을 취소했습니다. 현재 제안서는 변경하지 않았습니다.",
        )
        return Response(
            {
                "proposal": serialize_bid_proposal(proposal),
                "message": serialize_chat_message(assistant_message),
                "pendingRevisionCount": 0,
            }
        )

    if not pending_messages:
        return Response(
            {"error": "반영할 제안서 수정 요청이 없습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    instructions = []
    for message in pending_messages:
        metadata = message.sources[0] if message.sources else {}
        target = metadata.get("slide_number")
        instructions.append(
            f"{target}페이지: {message.content}"
            if target not in (None, "")
            else message.content
        )
    instruction = "\n".join(instructions)
    if len(instruction) > 3000:
        return Response(
            {"error": "한 번에 반영할 수정 요청은 합계 3,000자 이내로 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    slide_number = None
    if len(pending_messages) == 1:
        metadata = (
            pending_messages[0].sources[0]
            if pending_messages[0].sources
            else {}
        )
        slide_number = metadata.get("slide_number")
    if slide_number not in (None, ""):
        try:
            slide_number = int(slide_number)
        except (TypeError, ValueError):
            return Response(
                {"error": "슬라이드 번호를 확인해 주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        slide_number = None

    profile = CompanyProfile.objects.filter(user=request.user).first()
    if profile is None:
        return Response(
            {"error": "회사 정보를 먼저 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from .services.rag.proposal import revise_proposal_with_feedback

        result = revise_proposal_with_feedback(
            saved_bid=proposal.saved_bid,
            profile=profile,
            proposal=proposal,
            instruction=instruction,
            slide_number=slide_number,
        )
    except ValueError as error:
        BidChatMessage.objects.filter(
            id__in=[message.id for message in pending_messages]
        ).update(status=BidChatMessage.Status.FAILED)
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        BidChatMessage.objects.filter(
            id__in=[message.id for message in pending_messages]
        ).update(status=BidChatMessage.Status.FAILED)
        return Response(
            {"error": "수정 요청을 제안서에 반영하지 못했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    previous_file_name = proposal.generated_file.name
    current_plan = dict(proposal.revision_plan or {})
    feedback_plan = result["revision_plan"]
    feedback_history = list(current_plan.get("feedback_history", []))
    feedback_history.append(
        {
            "instruction": instruction,
            "slide_number": slide_number,
            "summary": feedback_plan.get("summary", ""),
            "company_claim_review": feedback_plan.get("company_claim_review"),
            "created_at": timezone.now().isoformat(),
        }
    )
    current_plan["status"] = "draft"
    current_plan["summary"] = feedback_plan.get("summary", current_plan.get("summary", ""))
    current_plan["output_slide_count"] = result["output_slide_count"]
    current_plan["feedback_history"] = feedback_history
    current_plan["revision_log"] = [
        *current_plan.get("revision_log", []),
        *result.get("revision_log", []),
    ]
    current_plan["quality_review"] = result.get(
        "quality_review",
        current_plan.get("quality_review", {}),
    )
    current_plan["final_review_items"] = list(
        dict.fromkeys(
            [
                *current_plan.get("final_review_items", []),
                *feedback_plan.get("final_review_items", []),
                *result.get("quality_review", {}).get("review_items", []),
            ]
        )
    )

    proposal.revision_plan = current_plan
    proposal.generated_file.save(
        result["filename"],
        ContentFile(result["file_bytes"]),
        save=False,
    )
    try:
        save_with_sqlite_retry(proposal)
    except Exception:
        proposal.generated_file.delete(save=False)
        return Response(
            {"error": "수정본은 생성됐지만 저장하지 못했습니다."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    from .services.proposal_preview import delete_proposal_preview

    delete_proposal_preview(proposal)
    if previous_file_name and previous_file_name != proposal.generated_file.name:
        proposal.generated_file.storage.delete(previous_file_name)

    BidChatMessage.objects.filter(
        id__in=[message.id for message in pending_messages]
    ).update(status=BidChatMessage.Status.APPLIED)
    assistant_message = BidChatMessage.objects.create(
        saved_bid=proposal.saved_bid,
        role=BidChatMessage.Role.ASSISTANT,
        message_type=BidChatMessage.MessageType.PROPOSAL,
        status=BidChatMessage.Status.APPLIED,
        content=(
            feedback_plan.get("summary")
            or "요청사항을 제안서에 반영했습니다."
        ),
        sources=feedback_plan.get("sources", []),
    )

    return Response(
        {
            "proposal": serialize_bid_proposal(proposal),
            "message": serialize_chat_message(assistant_message),
            "pendingRevisionCount": 0,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bid_proposal_finalize(request, bid_ntce_no):
    """사용자가 미리보기를 마치면 현재 초안을 최종본으로 확정합니다."""

    proposal = (
        BidProposal.objects.filter(
            saved_bid__user=request.user,
            saved_bid__bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("saved_bid__bid_notice")
        .first()
    )
    if proposal is None or not proposal.generated_file:
        return Response(
            {"error": "확정할 제안서 초안이 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if (proposal.revision_plan or {}).get("status") == "generating":
        return Response(
            {"error": "제안서 생성이 끝난 뒤 최종본을 만들어 주세요."},
            status=status.HTTP_409_CONFLICT,
        )

    proposal.revision_plan = {
        **(proposal.revision_plan or {}),
        "status": "final",
        "finalized_at": timezone.now().isoformat(),
    }
    save_with_sqlite_retry(proposal)
    return Response({"proposal": serialize_bid_proposal(proposal)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bid_proposal_download(request, bid_ntce_no):
    proposal = (
        BidProposal.objects.filter(
            saved_bid__user=request.user,
            saved_bid__bid_notice__bid_ntce_no=bid_ntce_no,
        )
        .select_related("saved_bid__bid_notice")
        .first()
    )
    if proposal is None or not proposal.generated_file:
        return Response(
            {"error": "생성된 제안서가 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if (proposal.revision_plan or {}).get("status", "final") != "final":
        return Response(
            {"error": "미리보기 확인 후 제안서 만들기를 눌러 최종본을 확정해 주세요."},
            status=status.HTTP_409_CONFLICT,
        )

    return FileResponse(
        proposal.generated_file.open("rb"),
        as_attachment=True,
        filename=f"bid2-proposal-{bid_ntce_no}.pptx",
        content_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
    )
