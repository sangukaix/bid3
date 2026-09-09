from django.contrib import admin

from .models import (
    BidAnalysis,
    BidChatMessage,
    BidNotice,
    BidProposal,
    BidQuantitativeProposal,
    CompanyDocument,
    CompanyKnowledgeItem,
    CompanyProfile,
    CompanyWebsitePage,
    ProjectReferenceDocument,
    RecommendedBid,
    SavedBid,
)


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "business_registration_number",
        "representative_name",
        "industry",
        "company_type",
        "updated_at",
    )
    search_fields = (
        "company_name",
        "business_registration_number",
        "representative_name",
        "user__username",
        "user__email",
    )
    list_filter = ("company_type", "preferred_bid_type")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CompanyDocument)
class CompanyDocumentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "user", "document_type", "uploaded_at")
    list_filter = ("document_type", "uploaded_at")
    search_fields = ("original_name", "user__username")
    readonly_fields = ("uploaded_at",)


@admin.register(CompanyKnowledgeItem)
class CompanyKnowledgeItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "source_document",
        "source_website_page",
        "user",
        "updated_at",
    )
    list_filter = ("category", "updated_at")
    search_fields = (
        "title",
        "content",
        "source_document__original_name",
        "source_website_page__url",
        "user__username",
    )
    readonly_fields = (
        "user",
        "source_document",
        "source_website_page",
        "category",
        "title",
        "content",
        "source_locations",
        "evidence_excerpt",
        "tags",
        "created_at",
        "updated_at",
    )


@admin.register(CompanyWebsitePage)
class CompanyWebsitePageAdmin(admin.ModelAdmin):
    list_display = ("title", "url", "user", "collected_at")
    search_fields = ("title", "url", "user__username")
    readonly_fields = (
        "user",
        "url",
        "title",
        "extracted_text",
        "content_hash",
        "collected_at",
        "created_at",
    )


@admin.register(BidNotice)
class BidNoticeAdmin(admin.ModelAdmin):
    list_display = (
        "bid_ntce_no",
        "title",
        "business_type",
        "notice_organization",
        "budget_amount",
        "close_at",
        "deadline_status",
        "is_active",
    )
    list_filter = (
        "deadline_status",
        "is_active",
        "business_type",
        "notice_date",
    )
    search_fields = (
        "bid_ntce_no",
        "title",
        "notice_organization",
        "demand_organization",
        "allowed_region",
        "allowed_industry",
    )
    ordering = ("close_at", "-notice_date")
    list_per_page = 50
    date_hierarchy = "notice_date"
    readonly_fields = ("raw_data", "created_at", "updated_at")


@admin.register(SavedBid)
class SavedBidAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "bid_notice",
        "proposal_started_at",
        "proposal_trashed_at",
        "created_at",
    )
    search_fields = (
        "user__username",
        "bid_notice__bid_ntce_no",
        "bid_notice__title",
    )
    readonly_fields = ("created_at",)


@admin.register(ProjectReferenceDocument)
class ProjectReferenceDocumentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "saved_bid", "processed_at", "uploaded_at")
    search_fields = (
        "original_name",
        "saved_bid__user__username",
        "saved_bid__bid_notice__bid_ntce_no",
    )
    readonly_fields = (
        "saved_bid",
        "file",
        "original_name",
        "extracted_knowledge",
        "content_hash",
        "processed_at",
        "uploaded_at",
    )


@admin.register(RecommendedBid)
class RecommendedBidAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "bid_notice",
        "match_score",
        "notification_sent_at",
        "created_at",
    )
    search_fields = ("user__username", "bid_notice__bid_ntce_no", "bid_notice__title")
    list_filter = ("notification_sent_at", "created_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BidAnalysis)
class BidAnalysisAdmin(admin.ModelAdmin):
    list_display = ("saved_bid", "created_at", "updated_at")
    search_fields = ("saved_bid__user__username", "saved_bid__bid_notice__bid_ntce_no")
    readonly_fields = ("report", "created_at", "updated_at")


@admin.register(BidChatMessage)
class BidChatMessageAdmin(admin.ModelAdmin):
    list_display = ("saved_bid", "role", "created_at")
    search_fields = ("saved_bid__user__username", "saved_bid__bid_notice__bid_ntce_no", "content")
    list_filter = ("role", "created_at")
    readonly_fields = ("saved_bid", "role", "content", "sources", "created_at")


@admin.register(BidProposal)
class BidProposalAdmin(admin.ModelAdmin):
    list_display = ("saved_bid", "output_format", "created_at", "updated_at")
    search_fields = ("saved_bid__user__username", "saved_bid__bid_notice__bid_ntce_no")
    list_filter = ("output_format", "template_mode", "created_at")
    readonly_fields = (
        "saved_bid",
        "output_format",
        "template_mode",
        "strategy",
        "revision_plan",
        "generated_file",
        "created_at",
        "updated_at",
    )


@admin.register(BidQuantitativeProposal)
class BidQuantitativeProposalAdmin(admin.ModelAdmin):
    list_display = ("saved_bid", "created_at", "updated_at")
    search_fields = (
        "saved_bid__user__username",
        "saved_bid__bid_notice__bid_ntce_no",
    )
    readonly_fields = (
        "saved_bid",
        "report",
        "generated_file",
        "created_at",
        "updated_at",
    )
