import json
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from ..llm import build_text_model
from ..local_context import structured_chain
from pydantic import BaseModel, Field

from .chatbot import CHAT_MODEL, build_full_page_context
from .prepare_docs_for_ai import prepare_docs_for_ai
from .retriever import search_bid_documents
from ..recommendation import get_profile_keywords


MAX_ANALYSIS_CONTEXT_CHARS = 30000  # 분석에 전달할 원문 길이 제한
MAX_ANALYSIS_OUTPUT_TOKENS = 3500  # 예상하지 못한 과도한 OpenAI 비용 방지
ANALYSIS_QUERIES = [
    "사업 개요 발주기관 사업 예산 입찰 마감 계약 기간 주요 과업",
    "입찰 참가 자격 면허 인증 실적 지역 제한 공동수급 신청 조건",
    "필수 제출 서류 기술평가 가격평가 평가 기준 배점",
    "요구 인력 자격 계약 조건 주의사항 위험 요소 과업 범위",
]


class ProjectOverview(BaseModel):
    ordering_organization: str = "확인 필요"
    budget: str = "확인 필요"
    bid_deadline: str = "확인 필요"
    contract_period: str = "확인 필요"
    project_summary: str


class EvaluationItem(BaseModel):
    name: str
    score: int = Field(ge=0)
    max_score: int = Field(gt=0)
    status: Literal[
        "충족",
        "회사정보 보완 필요",
        "공고문 확인 필요",
        "확인 필요",  # 기존에 저장된 분석 결과와 호환
        "미충족",
    ]
    explanation: str
    source_numbers: list[int] = Field(default_factory=list)


class BidAnalysisSchema(BaseModel):
    summary: str
    fit_score: int = Field(ge=0, le=100)
    recommendation: Literal["참여 검토", "조건부 검토", "참여 주의"]
    overview: ProjectOverview
    evaluation_items: list[EvaluationItem]
    eligibility: list[str]
    required_documents: list[str]
    technical_evaluation: list[str]
    price_evaluation: list[str]
    main_tasks: list[str]
    required_staff: list[str]
    certifications_and_experience: list[str]
    contract_cautions: list[str]
    strengths: list[str]
    risks: list[str]
    company_checks: list[str]
    action_strategy: list[str]


analysis_prompt = ChatPromptTemplate.from_template(
    """
[역할]
너는 나라장터 공고문과 회사 정보를 대조하는 입찰 검토 전문가입니다.

[중요 원칙]
- 아래 검색 문서와 회사 정보만 근거로 작성합니다.
- 적합도는 낙찰 확률이 아니라 공고 조건과 회사 역량의 일치 정도입니다.
- "확인 필요"만 단독으로 쓰지 말고 무엇이 부족한지 구체적으로 작성합니다.
- 회사 입력값이 비어 있으면 상태를 "회사정보 보완 필요"로 지정하고 누락 항목을 설명합니다.
- 공고 문서에서 근거를 찾지 못하면 상태를 "공고문 확인 필요"로 지정하고 확인할 문서를 설명합니다.
- 필수 자격을 충족하지 못할 가능성이 있으면 점수를 높게 주지 않습니다.
- 근거가 있는 항목에는 source_numbers에 출처 번호를 넣습니다.
- 평가 항목은 다음 5개를 사용하고 최대 점수 합계를 100으로 맞춥니다.
  1. 업종/분야 적합성 20점
  2. 기업 역량 및 규모 20점
  3. 지역 조건 10점
  4. 참가 자격 및 필수 요건 30점
  5. 사업 내용 및 실적 적합성 20점
- 한국어로 명확하고 실무적으로 작성합니다.

[회사 정보]
{company_context}

[공고 검색 문서]
{document_context}

[출력]
요구된 구조에 맞춰 공고와 회사의 적합성을 분석합니다.
"""
)


def build_analysis_chain():
    """AI 분석을 실제로 생성할 때만 OpenAI 클라이언트를 만듭니다."""

    analysis_model = build_text_model(
        "ANALYSIS", CHAT_MODEL, MAX_ANALYSIS_OUTPUT_TOKENS,
    )
    return structured_chain(analysis_prompt, analysis_model, BidAnalysisSchema)  # Prompt -> OpenAI -> Pydantic 결과


def collect_analysis_documents(bid_ntce_no):
    """분석 항목별로 검색한 문서 위치를 중복 없이 모읍니다."""

    documents = []
    used_documents = set()

    for query in ANALYSIS_QUERIES:
        for document in search_bid_documents(bid_ntce_no, query):
            key = (
                document.metadata.get("source"),
                document.metadata.get("element_index"),
                document.metadata.get("location"),
                document.page_content,
            )
            if key in used_documents:
                continue
            used_documents.add(key)
            documents.append(document)

    return documents


def company_context(profile):
    """Django 회사 프로필을 AI가 읽기 쉬운 JSON 문자열로 바꿉니다."""

    industries = list(
        dict.fromkeys(
            item.strip()
            for value in (profile.industry, profile.related_industries)
            for item in value.split(",")
            if item.strip()
        )
    )
    data = {
        "회사명": profile.company_name,
        "사업자등록번호": profile.business_registration_number,
        "대표자명": profile.representative_name,
        "전화번호": profile.phone,
        "이메일": profile.email,
        "회사홈페이지": [
            url for url in (profile.website_url_1, profile.website_url_2) if url
        ],
        "설립일": profile.established_date.isoformat() if profile.established_date else "미입력",
        "주소": profile.address,
        "사업분야": industries,
        "기업유형": profile.get_company_type_display() if profile.company_type else "미입력",
        "직원수": profile.employee_count,
        "자본금": profile.capital,
        "연매출": profile.annual_revenue,
        "주요사업": profile.main_business,
        "보유역량": profile.capabilities,
        "인증및자격": profile.licenses,
        "과거실적": profile.past_performance,
        "찾는공고키워드": get_profile_keywords(profile),
        "희망지역": profile.preferred_region,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def generate_bid_analysis(bid_ntce_no, profile):
    """공고 문서와 회사 정보를 분석해 저장 가능한 dict를 반환합니다."""

    prepare_docs_for_ai(bid_ntce_no)  # 최초 분석 때만 문서를 내려받아 벡터 DB 준비
    documents = collect_analysis_documents(bid_ntce_no)
    document_context, sources = build_full_page_context(
        documents,
        max_context_chars=MAX_ANALYSIS_CONTEXT_CHARS,
    )
    if not document_context:
        raise ValueError("분석에 사용할 공고 문서를 찾지 못했습니다.")

    result = build_analysis_chain().invoke(
        {
            "company_context": company_context(profile),
            "document_context": document_context,
        }
    )
    report = result.model_dump()
    report["sources"] = sources  # 화면과 PDF에서 확인할 원문 위치
    return report
