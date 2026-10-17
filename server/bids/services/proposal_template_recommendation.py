"""공고와 회사 업종에 맞는 제안서 디자인을 비용 없이 추천합니다."""


TEMPLATE_REASONS = {
    "corporate": "물품·구매 사업의 사양, 공급 계획과 회사 신뢰도를 정돈해 보여주기 적합합니다.",
    "modern": "IT·디지털 사업의 기술 구조와 단계별 수행 흐름을 선명하게 보여주기 적합합니다.",
    "public": "평가항목, 필수 요구사항과 수행 체계를 빠짐없이 대응하기 적합합니다.",
    "evergreen": "공사·시설·운영 사업의 현장 실행 계획과 품질관리 체계를 보여주기 적합합니다.",
    "burgundy": "교육·연구·컨설팅 사업의 전문성과 프로그램 차별성을 강조하기 적합합니다.",
}

TEMPLATE_KEYWORDS = {
    "corporate": (
        "구매", "납품", "장비", "기자재", "물품", "제조", "제품", "가구", "차량", "소모품",
    ),
    "modern": (
        "정보시스템", "소프트웨어", "플랫폼", "클라우드", "인공지능", "ai", "데이터",
        "디지털", "정보화", "시스템", "웹", "앱", "보안", "네트워크",
    ),
    "public": (
        "제안요청", "평가", "협상", "통합", "공공", "행정", "정부", "지자체", "정책",
    ),
    "evergreen": (
        "공사", "시설", "유지보수", "환경", "안전", "건축", "토목", "설비", "현장",
        "에너지", "전기", "소방", "운영관리",
    ),
    "burgundy": (
        "교육", "연수", "컨설팅", "연구", "조사", "홍보", "행사", "문화", "관광",
        "외국어", "인재", "역량강화", "워크숍",
    ),
}


def _contains_keyword(text, keywords):
    return any(keyword in text for keyword in keywords)


def recommend_proposal_template(bid_notice, profile=None):
    """프로젝트 성격을 점수화해 가장 잘 맞는 템플릿과 이유를 반환합니다."""

    # 발주기관 이름의 '공사'나 '교육원'보다 실제 과업을 우선합니다.
    title = str(bid_notice.title or "").lower()
    business_type = str(bid_notice.business_type or "").lower()
    domain = None
    if "물품" in business_type:
        domain = "supply_spec"
    elif "공사" in business_type:
        domain = "construction_site"
    elif (_contains_keyword(title, ("시스템", "플랫폼", "정보화", "포털", "소프트웨어"))
          and _contains_keyword(title, ("구축", "개발", "고도화", "전환", "개선"))):
        domain = "it_architecture"
    elif _contains_keyword(title, ("연구", "실태조사", "설문조사", "정책", "컨설팅", "타당성", "수요조사")):
        domain = "research_evidence"
    elif _contains_keyword(title, ("행사", "축제", "박람회", "전시", "홍보", "컨퍼런스", "포럼")):
        domain = "event_experience"
    elif _contains_keyword(title, TEMPLATE_KEYWORDS["modern"]):
        domain = "it_architecture"
    elif _contains_keyword(title, ("시공", "건축공사", "토목", "리모델링", "시설개선", "시설 개선", "보수공사")):
        domain = "construction_site"
    elif _contains_keyword(title, ("교육", "연수", "외국어", "직무훈련", "역량강화", "워크숍")):
        domain = "education_photo"
    elif _contains_keyword(title, TEMPLATE_KEYWORDS["corporate"]):
        domain = "supply_spec"
    domain_reasons = {
        "education_photo": "사진·회사 서비스 화면과 학습·운영 도식 중심의 구성입니다. 내부 검수표는 별도 PDF로 보관합니다.",
        "education_learning": "교육 과정표, 학습 흐름, 출석·평가와 교육 운영 일정 중심의 구조입니다.",
        "construction_site": "공종 WBS, 개념 공정표, 품질 승인점, 안전·준공 인계 중심의 구조입니다.",
        "it_architecture": "IT 시스템 구성, 요구사항 추적, 데이터 전환과 시험·개통 중심의 구조입니다.",
        "research_evidence": "연구 질문, 조사 설계, 분석·검증과 정책 대안 중심의 구조입니다.",
        "event_experience": "행사 콘셉트, 진행표, 참가자 동선과 현장·안전 운영 중심의 구조입니다.",
        "supply_spec": "물품 구성, 규격 대응표, 납품·설치와 검수·보증 중심의 구조입니다.",
    }
    if domain:
        return {"id": domain, "reason": domain_reasons[domain], "signals": ["공고 분야별 구조"]}

    project_text = " ".join(
        str(value or "").lower()
        for value in (
            bid_notice.title,
            bid_notice.business_type,
            bid_notice.contract_method,
            bid_notice.notice_organization,
            bid_notice.demand_organization,
        )
    )
    company_text = " ".join(
        str(value or "").lower()
        for value in (
            getattr(profile, "industry", ""),
            getattr(profile, "related_industries", ""),
            getattr(profile, "main_business", ""),
        )
    )

    scores = {
        "corporate": 10,
        "modern": 10,
        "public": 25,  # 명확한 신호가 없으면 공공입찰 실무형을 기본 추천
        "evergreen": 10,
        "burgundy": 10,
    }
    matched_signals = {template_id: [] for template_id in scores}

    business_type = str(bid_notice.business_type or "").lower()
    if "물품" in business_type:
        scores["corporate"] += 35
        matched_signals["corporate"].append("물품")
    elif "공사" in business_type:
        scores["evergreen"] += 35
        matched_signals["evergreen"].append("공사")
    elif "용역" in business_type:
        scores["public"] += 10

    for template_id, keywords in TEMPLATE_KEYWORDS.items():
        if _contains_keyword(project_text, keywords):
            # 공공 입찰이라는 사실보다 사업의 전문 분야를 더 강하게 반영합니다.
            scores[template_id] += 15 if template_id == "public" else 35
            matched_signals[template_id].append("공고 내용")
        if _contains_keyword(company_text, keywords):
            scores[template_id] += 8
            matched_signals[template_id].append("회사 업종")

    priority = ["modern", "burgundy", "evergreen", "corporate", "public"]
    recommended_id = max(
        priority,
        key=lambda template_id: (scores[template_id], -priority.index(template_id)),
    )
    return {
        "id": recommended_id,
        "reason": TEMPLATE_REASONS[recommended_id],
        "signals": matched_signals[recommended_id],
    }
