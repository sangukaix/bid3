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
