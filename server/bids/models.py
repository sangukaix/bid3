from pathlib import Path
import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


class CompanyProfile(models.Model):
    class CompanyType(models.TextChoices):
        SMALL_MEDIUM = "small-medium", "중소기업"
        SMALL = "small", "소기업"
        MICRO = "micro", "소상공인"
        OTHER = "other", "기타"

    class PreferredBidType(models.TextChoices):
        SERVICE = "service", "용역"
        GOODS = "goods", "물품"
        CONSTRUCTION = "construction", "공사"

    # 회원 한 명과 회사 프로필 하나를 연결
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_profile",
    )

    # 회사 기본 정보
    company_name = models.CharField(max_length=200)
    business_registration_number = models.CharField(max_length=20, unique=True)
    representative_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website_url_1 = models.URLField(blank=True)
    website_url_2 = models.URLField(blank=True)
    established_date = models.DateField(null=True, blank=True)
    address = models.TextField()

    # 회사 자격과 수행 역량
    industry = models.CharField(max_length=200)
    related_industries = models.TextField(blank=True)  # 대표 업종 외 관련 업종을 쉼표로 구분해 저장
    company_type = models.CharField(
        max_length=20,
        choices=CompanyType.choices,
        blank=True,
    )
    employee_count = models.PositiveIntegerField(null=True, blank=True)
    capital = models.PositiveBigIntegerField(null=True, blank=True)
    annual_revenue = models.PositiveBigIntegerField(null=True, blank=True)
    main_business = models.TextField()
    capabilities = models.TextField(blank=True)
    licenses = models.TextField(blank=True)
    past_performance = models.TextField(blank=True)

    # 사용자가 원하는 입찰 조건
    required_keywords = models.TextField(blank=True)  # 기존 데이터 호환용, preferred_keywords와 합쳐 사용
    preferred_keywords = models.TextField()
    excluded_keywords = models.TextField(blank=True)  # 포함되면 추천에서 제외할 검색어
    preferred_bid_type = models.CharField(
        max_length=20,
        choices=PreferredBidType.choices,
        blank=True,
    )
    preferred_region = models.CharField(max_length=200, blank=True)

    # 최초 저장 시간과 마지막 수정 시간
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name


def company_document_upload_path(instance, filename):
    """사용자별 폴더에 충돌하지 않는 파일명으로 회사 문서를 저장합니다."""

    extension = Path(filename).suffix.lower()
    return f"company_documents/user_{instance.user_id}/{uuid.uuid4().hex}{extension}"


class CompanyDocument(models.Model):
    class DocumentType(models.TextChoices):
        PROPOSAL = "proposal", "제안서"
        COMPANY_INTRODUCTION = "company_introduction", "회사소개서"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_documents",
    )
    file = models.FileField(upload_to=company_document_upload_path)
    original_name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)

    def delete(self, *args, **kwargs):
        stored_file = self.file
        super().delete(*args, **kwargs)
        stored_file.delete(save=False)  # DB 기록 삭제 후 실제 업로드 파일도 함께 삭제

    def __str__(self):
        return self.original_name


class CompanyWebsitePage(models.Model):
    """회사 홈페이지에서 수집해 다시 사용할 수 있도록 저장한 페이지입니다."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_website_pages",
    )
    url = models.URLField(max_length=1000)
    title = models.CharField(max_length=300, blank=True)
    extracted_text = models.TextField()
    content_hash = models.CharField(max_length=64)
    collected_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("url",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "url"),
                name="unique_user_company_website_page",
            )
        ]

    def __str__(self):
        return self.title or self.url


class CompanyKnowledgeItem(models.Model):
    class Category(models.TextChoices):
        COMPANY_OVERVIEW = "company_overview", "회사 개요"
        HISTORY = "history", "연혁"
        PERSONNEL = "personnel", "인력"
        INFRASTRUCTURE = "infrastructure", "인프라"
        CAPABILITY = "capability", "기술·역량"
        PERFORMANCE = "performance", "수행 실적"
        METHODOLOGY = "methodology", "수행 방법론"
        STRENGTH = "strength", "강점·차별점"
        CERTIFICATION = "certification", "면허·인증"
        OTHER = "other", "기타"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_knowledge_items",
    )
    source_document = models.ForeignKey(
        CompanyDocument,
        on_delete=models.CASCADE,
        related_name="knowledge_items",
        null=True,
        blank=True,
    )  # 회사 문서에서 추출한 지식의 출처
    source_website_page = models.ForeignKey(
        CompanyWebsitePage,
        on_delete=models.CASCADE,
        related_name="knowledge_items",
        null=True,
        blank=True,
    )  # 회사 홈페이지에서 추출한 지식의 출처
    category = models.CharField(max_length=30, choices=Category.choices)
    title = models.CharField(max_length=200)
    content = models.TextField()
    source_locations = models.JSONField(default=list, blank=True)
    evidence_excerpt = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("category", "title")
        indexes = [
            models.Index(
                fields=("user", "category"),
                name="company_know_user_category",
            ),
            models.Index(
                fields=("source_document", "category"),
                name="company_know_doc_category",
            ),
            models.Index(
                fields=("source_website_page", "category"),
                name="company_know_web_category",
            ),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.title}"


class BidNotice(models.Model):
    class DeadlineStatus(models.TextChoices):
        ACTIVE = "active", "유효"
        EXPIRED = "expired", "마감"
        REVIEW = "review", "확인 필요"

    # 나라장터에서 공고를 구분하는 기본 정보
    bid_ntce_no = models.CharField(max_length=50)
    bid_ntce_ord = models.CharField(max_length=10, default="000")

    # 목록과 검색에서 자주 사용하는 정보
    title = models.CharField(max_length=500)
    status = models.CharField(max_length=50, blank=True)
    business_type = models.CharField(max_length=50, blank=True)
    contract_method = models.CharField(max_length=100, blank=True)

    # 공고기관과 수요기관
    notice_organization = models.CharField(max_length=200, blank=True)
    demand_organization = models.CharField(max_length=200, blank=True)

    # 공고 일정
    notice_date = models.DateField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)
    deadline_status = models.CharField(
        max_length=20,
        choices=DeadlineStatus.choices,
        default=DeadlineStatus.REVIEW,
    )

    # 공고 금액
    budget_amount = models.BigIntegerField(null=True, blank=True)
    estimated_price = models.BigIntegerField(null=True, blank=True)

    # 참가 제한
    region_limit = models.BooleanField(default=False)
    allowed_region = models.TextField(blank=True)
    industry_limit = models.BooleanField(default=False)
    allowed_industry = models.TextField(blank=True)

    # 나라장터 원문 주소
    source_url = models.URLField(max_length=1000, blank=True)

    # API가 보내준 53개 필드를 원본 그대로 보관
    raw_data = models.JSONField(default=dict, blank=True)

    # 공고 활성 상태와 저장 시간
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bid_ntce_no", "bid_ntce_ord"],
                name="unique_bid_notice",
            )
        ]

    def __str__(self):
        return f"{self.bid_ntce_no} - {self.title}"


class SavedBid(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_bids",
    )  # 어떤 회원이 저장했는지 연결
    bid_notice = models.ForeignKey(
        BidNotice,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )  # 어떤 입찰공고를 저장했는지 연결
    proposal_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )  # 사용자가 제안서 만들기를 눌러 프로젝트를 시작한 시간
    proposal_trashed_at = models.DateTimeField(
        null=True,
        blank=True,
    )  # 값이 있으면 제안서 프로젝트만 휴지통에 보관
    created_at = models.DateTimeField(auto_now_add=True)  # 공고를 저장한 시간

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "bid_notice"],
                name="unique_user_saved_bid",
            )
        ]  # 같은 회원이 같은 공고를 중복 저장하지 못하게 함
        ordering = ["-created_at"]  # 최근에 저장한 공고부터 조회

    def __str__(self):
        return f"{self.user.username} - {self.bid_notice.bid_ntce_no}"


def project_reference_upload_path(instance, filename):
    """프로젝트별 참고 제안서를 사용자와 공고별 폴더에 저장합니다."""

    extension = Path(filename).suffix.lower()
    bid_number = instance.saved_bid.bid_notice.bid_ntce_no
    return (
        f"project_reference_documents/user_{instance.saved_bid.user_id}/"
        f"{bid_number}/{uuid.uuid4().hex}{extension}"
    )


class ProjectReferenceDocument(models.Model):
    """현재 공고의 제안서 생성에만 사용하는 유사 제안서입니다."""

    saved_bid = models.ForeignKey(
        SavedBid,
        on_delete=models.CASCADE,
        related_name="reference_documents",
    )
    file = models.FileField(upload_to=project_reference_upload_path)
    original_name = models.CharField(max_length=255)
    extracted_knowledge = models.JSONField(default=list, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)

    def delete(self, *args, **kwargs):
        stored_file = self.file
        super().delete(*args, **kwargs)
        stored_file.delete(save=False)

    def __str__(self):
        return self.original_name


class RecommendedBid(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommended_bids",
    )  # 추천받은 회원
    bid_notice = models.ForeignKey(
        BidNotice,
        on_delete=models.CASCADE,
        related_name="recommended_to_users",
    )  # 조건과 일치한 공고
    match_score = models.PositiveSmallIntegerField(default=0)
    title_match_count = models.PositiveSmallIntegerField(default=0)
    matched_keywords = models.JSONField(default=list, blank=True)
    match_reasons = models.JSONField(default=list, blank=True)
    is_match = models.BooleanField(default=True)  # 현재 회사 조건에도 계속 맞는 공고인지 표시
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "bid_notice"],
                name="unique_user_recommended_bid",
            )
        ]  # 같은 회원에게 같은 공고를 두 번 추천하거나 알리지 않음
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.bid_notice.bid_ntce_no}"


class BidAnalysis(models.Model):
    saved_bid = models.OneToOneField(
        SavedBid,
        on_delete=models.CASCADE,
        related_name="analysis",
    )  # 회원이 저장한 공고 하나와 분석 결과 하나를 연결
    report = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.saved_bid} AI 분석"


class BidChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "사용자"
        ASSISTANT = "assistant", "AI"

    class MessageType(models.TextChoices):
        QUESTION = "question", "공고 질문"
        PROPOSAL = "proposal", "제안서 수정"

    class Status(models.TextChoices):
        APPLIED = "applied", "처리 완료"
        PENDING = "pending", "반영 대기"
        FAILED = "failed", "처리 실패"

    saved_bid = models.ForeignKey(
        SavedBid,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )  # 회원이 저장한 공고와 대화 내용을 연결
    role = models.CharField(max_length=10, choices=Role.choices)
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.QUESTION,
    )  # 하나의 대화창 안에서 공고 질문과 제안서 수정 요청을 구분
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.APPLIED,
    )
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.saved_bid} - {self.get_role_display()}"


def bid_proposal_upload_path(instance, filename):
    """생성된 제안서를 사용자별 폴더에 안전한 파일명으로 저장합니다."""

    extension = Path(filename).suffix.lower()
    return f"generated_proposals/user_{instance.saved_bid.user_id}/{uuid.uuid4().hex}{extension}"


class BidProposal(models.Model):
    class OutputFormat(models.TextChoices):
        DOCX = "docx", "Word"
        PPTX = "pptx", "PowerPoint"

    saved_bid = models.OneToOneField(
        SavedBid,
        on_delete=models.CASCADE,
        related_name="proposal",
    )  # 회원이 저장한 공고 하나와 생성 제안서 하나를 연결
    output_format = models.CharField(max_length=10, choices=OutputFormat.choices)
    template_mode = models.CharField(max_length=30, default="default_template")
    strategy = models.JSONField(default=dict)
    revision_plan = models.JSONField(default=dict)
    generated_file = models.FileField(upload_to=bid_proposal_upload_path)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.saved_bid} 제안서"


@receiver(post_delete, sender=BidProposal)
def delete_bid_proposal_file(sender, instance, **kwargs):
    """저장 공고가 삭제되면 생성된 제안서 파일도 함께 정리합니다."""

    from .services.proposal_preview import delete_proposal_preview

    delete_proposal_preview(instance)
    if instance.generated_file:
        instance.generated_file.delete(save=False)


def bid_quantitative_upload_path(instance, filename):
    """정량평가 작성안을 사용자별 폴더에 저장합니다."""

    extension = Path(filename).suffix.lower()
    return f"generated_quantitative/user_{instance.saved_bid.user_id}/{uuid.uuid4().hex}{extension}"


class BidQuantitativeProposal(models.Model):
    saved_bid = models.OneToOneField(
        SavedBid,
        on_delete=models.CASCADE,
        related_name="quantitative_proposal",
    )  # 저장 공고 하나에 최신 정량평가 작성안 하나를 연결
    report = models.JSONField(default=dict)
    generated_file = models.FileField(
        upload_to=bid_quantitative_upload_path,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.saved_bid} 정량평가 작성안"


@receiver(post_delete, sender=BidQuantitativeProposal)
def delete_bid_quantitative_file(sender, instance, **kwargs):
    """저장 공고가 삭제되면 정량평가 Word 파일도 함께 정리합니다."""

    if instance.generated_file:
        instance.generated_file.delete(save=False)
