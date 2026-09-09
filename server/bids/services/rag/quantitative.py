import os
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from ..llm import build_text_model
from pydantic import BaseModel, Field

from ..company_knowledge import build_company_knowledge_context
from .analysis import company_context
from .chatbot import build_full_page_context
from .document_requirements import (
    build_document_requirement_register,
    build_requirement_context,
)
from .prepare_docs_for_ai import prepare_docs_for_ai
from .proposal import collect_proposal_documents
from .retriever import search_bid_documents


QUANTITATIVE_MODEL = os.getenv("PROPOSAL_MODEL", "gpt-5.6-sol")
MAX_QUANTITATIVE_CONTEXT_CHARS = 70000
MAX_QUANTITATIVE_OUTPUT_TOKENS = 12000
QUANTITATIVE_QUERIES = [
    "정량평가 객관적 평가 평가항목 배점 산정 기준",
    "경영상태 신용평가 재무제표 매출액 자본금 기업 규모",
    "유사사업 수행실적 실적증명서 계약서 세금계산서",
    "투입인력 기술자 경력 자격증 재직증명서 4대보험",
    "면허 인증 신고 등록 참가자격 증빙서류",
    "정량 제안서 별지 서식 제출 양식 증빙자료",
]


class QuantitativeItem(BaseModel):
    category: Literal[
        "기업 일반",
        "재무·신용",
        "수행 실적",
        "투입 인력",
        "면허·인증",
        "제출 서식",
        "기타",
    ]
    requirement: str
    form_name: str = ""
    evaluation_points: str = "확인 필요"
    status: Literal["작성 가능", "자료 필요", "담당자 확인"]
    prepared_content: str
    company_evidence: list[str] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    source_numbers: list[int] = Field(default_factory=list)


class QuantitativeFormField(BaseModel):
    label: str
    value: str = ""
    status: Literal["작성 완료", "미작성", "직접 확인"]
    missing_reason: str = ""
    company_evidence: list[str] = Field(default_factory=list)
    source_numbers: list[int] = Field(default_factory=list)


class QuantitativeForm(BaseModel):
    form_name: str
    purpose: str = ""
    source_file: str = ""
    source_location: str = ""
    fields: list[QuantitativeFormField] = Field(default_factory=list)


class QuantitativeProposalSchema(BaseModel):
    required: bool
    summary: str
    completion_score: int = Field(ge=0, le=100)
    items: list[QuantitativeItem] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    forms: list[QuantitativeForm] = Field(default_factory=list)


quantitative_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
당신은 공공 입찰 정량평가 서류를 준비하는 실무 담당자입니다.

[목표]
- 공고문, 제안요청서, 과업지시서와 별지 서식에서 정량평가 요구사항을 찾습니다.
- 첨부문서에 실제로 존재하는 정량평가 양식을 찾아 forms에 양식별 입력칸을 순서대로 정리합니다.
- 회사 정보와 회사 문서로 작성 가능한 칸은 채우고, 작성할 근거가 없는 칸은 빈 문자열로 남깁니다.

[엄격한 원칙]
- 제공된 자료에 없는 매출, 인력, 자격, 실적, 점수와 날짜를 절대 만들어내지 않습니다.
- 근거가 있으면 "작성 가능", 자료가 없으면 "자료 필요", 해석이나 담당자 판단이 필요하면 "담당자 확인"으로 표시합니다.
- 정량평가 제출 요구가 문서에 없으면 required=false로 표시하고 추측해서 항목을 만들지 않습니다.
- 배점과 서식명은 문서에 적힌 경우에만 기록합니다.
- prepared_content는 그대로 제출하는 완성본이 아니라 담당자가 검증할 수 있는 작성 초안으로 씁니다.
- 각 항목에 공고 출처 번호를 연결합니다.
- 문서에 없는 양식이나 입력칸은 새로 만들지 않습니다.
- forms의 value는 제공 자료로 확정할 수 있을 때만 작성합니다.
- 회사 홈페이지 내용은 참고 정보입니다. 면허·인증·재무·실적처럼 공식 증빙이 필요한 값은 업로드 문서나 회사 입력 정보로 확인될 때만 확정합니다.
- 값이 없으면 value=""로 두고 status="미작성", 서명·날인·선택 판단이 필요하면 status="직접 확인"으로 표시합니다.
- 양식명, 원본 파일명과 페이지 또는 문서 위치를 가능한 범위에서 기록합니다.
- 한국어로 간결하고 정확하게 작성합니다.
""",
        ),
        (
            "human",
            """
[회사 입력 정보]
{company_context}

[회사 문서에서 확인한 자료]
{company_knowledge_context}

[공고 문서]
{document_context}

[모든 첨부문서에서 추출한 요구사항 목록]
{requirement_context}

정량평가 제출 여부와 작성 가능한 항목, 추가로 필요한 증빙자료를 구조화해 주세요.
""",
        ),
    ]
)


def collect_quantitative_documents(bid_ntce_no):
    """정량평가와 증빙 요구가 있는 문서 위치를 중복 없이 모읍니다."""

    documents = []
    used = set()
    for query in QUANTITATIVE_QUERIES:
        for document in search_bid_documents(bid_ntce_no, query):
            key = (
                document.metadata.get("source"),
                document.metadata.get("element_index"),
                document.metadata.get("location"),
            )
            if key in used:
                continue
            used.add(key)
            documents.append(document)
    return documents


def build_quantitative_model():
    """정량평가 생성 시에만 OpenAI 모델을 준비합니다."""

    return build_text_model(
        "QUANTITATIVE", QUANTITATIVE_MODEL, MAX_QUANTITATIVE_OUTPUT_TOKENS,
    ).with_structured_output(QuantitativeProposalSchema)


def add_completion_summary(report):
    """양식의 실제 작성값을 기준으로 완료·미작성 목록을 계산합니다."""

    completed_fields = []
    incomplete_fields = []
    direct_review_fields = []
    for form in report.get("forms", []):
        form_name = form.get("form_name") or "정량평가 양식"
        for field in form.get("fields", []):
            label = field.get("label") or "항목명 확인 필요"
            value = str(field.get("value") or "").strip()
            status = field.get("status")
            item_name = f"{form_name} · {label}"
            if value:
                field["status"] = "작성 완료"
                completed_fields.append(item_name)
            elif status == "직접 확인":
                direct_review_fields.append(item_name)
            else:
                field["status"] = "미작성"
                incomplete_fields.append(item_name)

    total = len(completed_fields) + len(incomplete_fields) + len(direct_review_fields)
    report["completion"] = {
        "form_count": len(report.get("forms", [])),
        "total_fields": total,
        "completed_fields": len(completed_fields),
        "incomplete_fields": len(incomplete_fields),
        "direct_review_fields": len(direct_review_fields),
    }
    report["completed_field_names"] = completed_fields
    report["incomplete_field_names"] = incomplete_fields
    report["direct_review_field_names"] = direct_review_fields
    if total:
        report["completion_score"] = round(len(completed_fields) / total * 100)
    return report


def generate_quantitative_proposal(saved_bid, profile):
    """공고와 회사 자료를 대조해 정량평가 작성안 dict를 만듭니다."""

    processing = prepare_docs_for_ai(saved_bid.bid_notice.bid_ntce_no)
    all_documents = collect_proposal_documents(saved_bid.bid_notice.bid_ntce_no)
    requirement_register, requirement_processing = (
        build_document_requirement_register(
            saved_bid.bid_notice.bid_ntce_no,
            all_documents,
        )
    )
    documents = collect_quantitative_documents(saved_bid.bid_notice.bid_ntce_no)
    document_context, sources = build_full_page_context(
        documents,
        max_context_chars=MAX_QUANTITATIVE_CONTEXT_CHARS,
    )
    if not document_context:
        raise ValueError("정량평가 요구사항을 확인할 공고 문서를 찾지 못했습니다.")

    company_knowledge_context, company_processing = build_company_knowledge_context(
        saved_bid.user,
        max_chars=50000,
    )
    result = (quantitative_prompt | build_quantitative_model()).invoke(
        {
            "company_context": company_context(profile),
            "company_knowledge_context": company_knowledge_context,
            "document_context": document_context,
            "requirement_context": build_requirement_context(requirement_register),
        }
    )
    report = add_completion_summary(result.model_dump())
    report["sources"] = sources
    report["document_processing"] = processing
    report["requirement_processing"] = requirement_processing
    report["company_document_processing"] = company_processing
    return report
