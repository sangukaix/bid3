from django.db.models import Q
from django.utils import timezone

from bids.models import BidNotice, CompanyProfile, RecommendedBid


MAX_RECOMMENDATIONS = 10  # 추천 페이지에 저장할 최대 공고 수
MIN_RECOMMENDATION_SCORE = 30  # 너무 약하게 일치하는 공고 제외
PREFERRED_BID_TYPE_MAP = {
    "service": "용역",
    "goods": "물품",
    "construction": "공사",
}
REGION_ALIASES = {
    "충북": ("충북", "충청북도"),
    "충남": ("충남", "충청남도"),
    "전북": ("전북", "전라북도"),
    "전남": ("전남", "전라남도"),
    "경북": ("경북", "경상북도"),
    "경남": ("경남", "경상남도"),
}


def parse_conditions(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def get_profile_keywords(profile):
    """기존 두 필드의 값을 하나의 중복 없는 추천 키워드 목록으로 합칩니다."""

    return list(
        dict.fromkeys(
            parse_conditions(profile.required_keywords)
            + parse_conditions(profile.preferred_keywords)
        )
    )


def delete_expired_recommendations(user):
    """마감되었거나 비활성화된 추천공고 기록을 실제 DB에서 삭제합니다."""

    deleted_count, _ = RecommendedBid.objects.filter(user=user).filter(
        Q(bid_notice__is_active=False)
        | Q(bid_notice__deadline_status=BidNotice.DeadlineStatus.EXPIRED)
        | Q(bid_notice__close_at__lt=timezone.now())
    ).delete()
    return deleted_count


def matches_region(notice, preferred_regions):
    if not preferred_regions or not notice.region_limit:
        return True

    allowed_region = notice.allowed_region.lower()
    return any(
        alias.lower() in allowed_region
        for region in preferred_regions
        for alias in REGION_ALIASES.get(region, (region,))
    )


def build_recommendation(
    notice,
    profile,
    keywords,
    excluded_keywords,
    preferred_regions,
):
    """공고 한 건이 회사 조건에 맞는지 확인하고 규칙 점수를 계산합니다."""

    title = notice.title.lower()
    secondary_text = " ".join(
        [
            notice.allowed_industry,
            notice.notice_organization,
            notice.demand_organization,
        ]
    ).lower()
    searchable_text = f"{title} {secondary_text}"

    # 제외 단어가 하나라도 있으면 추천하지 않습니다.
    if any(keyword.lower() in searchable_text for keyword in excluded_keywords):
        return None

    matched_keywords = [
        keyword for keyword in keywords if keyword.lower() in searchable_text
    ]
    if not matched_keywords:
        return None

    preferred_type = PREFERRED_BID_TYPE_MAP.get(profile.preferred_bid_type)
    if preferred_type and notice.business_type != preferred_type:
        return None
    if not matches_region(notice, preferred_regions):
        return None

    score = 0
    reasons = []
    title_matches = [keyword for keyword in matched_keywords if keyword.lower() in title]
    secondary_matches = [
        keyword for keyword in matched_keywords if keyword.lower() in secondary_text
    ]

    if title_matches:
        title_score = min(40 + (len(title_matches) - 1) * 10, 60)
        score += title_score
        reasons.append(
            f"공고명 키워드 {len(title_matches)}개 일치 (+{title_score}점): "
            f"{', '.join(title_matches)}"
        )
    if secondary_matches:
        secondary_score = min(10 + (len(secondary_matches) - 1) * 5, 15)
        score += secondary_score
        reasons.append(
            f"업종·기관 키워드 {len(secondary_matches)}개 일치 (+{secondary_score}점): "
            f"{', '.join(secondary_matches)}"
        )
    if preferred_type:
        score += 10
        reasons.append(f"업무 구분 일치 (+10점): {preferred_type}")
    if preferred_regions:
        score += 10
        region_reason = "전국 참가 가능" if not notice.region_limit else "희망 지역 일치"
        reasons.append(f"{region_reason} (+10점)")
    if score < MIN_RECOMMENDATION_SCORE:
        return None

    return {
        "match_score": min(score, 100),
        "title_match_count": len(title_matches),
        "matched_keywords": matched_keywords,
        "match_reasons": reasons,
    }


def match_user_recommendations(user):
    delete_expired_recommendations(user)  # 새 추천을 만들기 전에 지난 추천공고 정리

    profile = CompanyProfile.objects.filter(user=user).first()
    if profile is None:
        return {"checked": 0, "created": 0, "updated": 0}

    keywords = get_profile_keywords(profile)
    excluded_keywords = parse_conditions(profile.excluded_keywords)
    preferred_regions = parse_conditions(profile.preferred_region)

    # 과거 기록과 알림 이력은 보존하고 이번 상위 추천만 다시 활성화합니다.
    RecommendedBid.objects.filter(user=user).update(is_match=False)
    if not keywords:
        return {"checked": 0, "created": 0, "updated": 0}

    keyword_condition = Q()
    for keyword in keywords:
        keyword_condition |= (
            Q(title__icontains=keyword)
            | Q(allowed_industry__icontains=keyword)
            | Q(notice_organization__icontains=keyword)
            | Q(demand_organization__icontains=keyword)
        )

    notices = BidNotice.objects.filter(is_active=True).filter(
        Q(close_at__isnull=True) | Q(close_at__gte=timezone.now())
    ).filter(keyword_condition)
    checked_count = notices.count()
    ranked_matches = []

    for notice in notices.iterator():
        match_data = build_recommendation(
            notice,
            profile,
            keywords,
            excluded_keywords,
            preferred_regions,
        )
        if match_data is not None:
            ranked_matches.append((notice, match_data))

    ranked_matches.sort(
        key=lambda item: (
            item[1]["match_score"],
            item[1]["title_match_count"],
            item[0].notice_date.toordinal() if item[0].notice_date else 0,
            item[0].close_at.timestamp() if item[0].close_at else 0,
        ),
        reverse=True,
    )

    created_count = 0
    updated_count = 0
    for notice, match_data in ranked_matches[:MAX_RECOMMENDATIONS]:
        recommendation, created = RecommendedBid.objects.get_or_create(
            user=user,
            bid_notice=notice,
            defaults={**match_data, "is_match": True},
        )
        if created:
            created_count += 1
            continue

        match_data["is_match"] = True
        changed = any(
            getattr(recommendation, field) != value
            for field, value in match_data.items()
        )
        if changed:
            for field, value in match_data.items():
                setattr(recommendation, field, value)
            recommendation.save(
                update_fields=[
                    "match_score",
                    "title_match_count",
                    "matched_keywords",
                    "match_reasons",
                    "is_match",
                    "updated_at",
                ]
            )
            updated_count += 1

    return {
        "checked": checked_count,
        "created": created_count,
        "updated": updated_count,
    }
