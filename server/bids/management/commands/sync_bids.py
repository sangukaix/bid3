from datetime import datetime, timedelta
from math import ceil

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from bids.models import BidNotice
from bids.services.g2b_api import fetch_bid_notices


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def parse_datetime(date_value, time_value):
    if not date_value:
        return None

    time_value = time_value or "23:59"

    try:
        date_time = datetime.strptime(
            f"{date_value} {time_value}",
            "%Y-%m-%d %H:%M",
        )
    except (TypeError, ValueError):
        return None

    return timezone.make_aware(
        date_time,
        timezone.get_current_timezone(),
    )


def parse_amount(value):
    if not value:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_yes_no(value):
    return value == "Y"


def determine_deadline_status(status, close_at):
    if status == "취소공고":
        return BidNotice.DeadlineStatus.EXPIRED

    if close_at is None:
        return BidNotice.DeadlineStatus.REVIEW

    if close_at <= timezone.now():
        return BidNotice.DeadlineStatus.EXPIRED

    return BidNotice.DeadlineStatus.ACTIVE


def notice_order(item):
    try:
        return int(item.get("bidNtceOrd") or 0)
    except (TypeError, ValueError):
        return 0


def update_latest_notices(latest_notices, items):
    for item in items:
        bid_ntce_no = item.get("bidNtceNo")

        if not bid_ntce_no:
            continue

        previous = latest_notices.get(bid_ntce_no)

        if previous is None or notice_order(item) >= notice_order(previous):
            latest_notices[bid_ntce_no] = item


def build_notice_defaults(item, status, close_at, deadline_status):
    return {
        "title": item.get("bidNtceNm", ""),
        "status": status,
        "business_type": item.get("bsnsDivNm", ""),
        "contract_method": item.get("cntrctCnclsMthdNm", ""),
        "notice_organization": item.get("ntceInsttNm", ""),
        "demand_organization": item.get("dmndInsttNm", ""),
        "notice_date": parse_date(item.get("bidNtceDate")),
        "close_at": close_at,
        "deadline_status": deadline_status,
        "budget_amount": parse_amount(item.get("asignBdgtAmt")),
        "estimated_price": parse_amount(item.get("presmptPrce")),
        "region_limit": parse_yes_no(item.get("rgnLmtYn")),
        "allowed_region": item.get("prtcptPsblRgnNm", ""),
        "industry_limit": parse_yes_no(item.get("indstrytyLmtYn")),
        "allowed_industry": item.get("bidprcPsblIndstrytyNm", ""),
        "source_url": item.get("bidNtceUrl", ""),
        "raw_data": item,
        # 확인 필요 공고도 경고를 붙여 추천하므로 후보 상태를 유지한다.
        "is_active": deadline_status != BidNotice.DeadlineStatus.EXPIRED,
    }


class Command(BaseCommand):
    help = "나라장터 입찰공고를 수집합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-pages",
            type=int,
            help="시험 실행에서 가져올 최대 페이지 수",
        )

    def handle(self, *args, **options):
        max_pages = options["max_pages"]

        if max_pages is not None and max_pages < 1:
            raise CommandError("--max-pages는 1 이상이어야 합니다.")

        page_size = 999
        end_at = timezone.localtime().replace(second=0, microsecond=0)
        start_at = end_at - timedelta(days=30)

        self.stdout.write(
            f"나라장터 API 요청: {start_at:%Y-%m-%d %H:%M} ~ "
            f"{end_at:%Y-%m-%d %H:%M}"
        )

        first_data = fetch_bid_notices(
            page_no=1,
            num_of_rows=page_size,
            start_at=start_at,
            end_at=end_at,
        )
        first_body = first_data["response"]["body"]
        total_count = int(first_body.get("totalCount") or 0)
        total_pages = ceil(total_count / page_size) if total_count else 0
        pages_to_fetch = total_pages

        if max_pages is not None:
            pages_to_fetch = min(total_pages, max_pages)

        latest_notices = {}
        first_items = first_body.get("items") or []
        fetched_count = len(first_items)
        update_latest_notices(latest_notices, first_items)

        self.stdout.write(
            f"API 전체 검색 결과: {total_count:,}건 / "
            f"전체 {total_pages}페이지"
        )

        for page_no in range(2, pages_to_fetch + 1):
            page_data = fetch_bid_notices(
                page_no=page_no,
                num_of_rows=page_size,
                start_at=start_at,
                end_at=end_at,
            )
            page_items = page_data["response"]["body"].get("items") or []
            fetched_count += len(page_items)
            update_latest_notices(latest_notices, page_items)
            self.stdout.write(
                f"페이지 수집: {page_no}/{pages_to_fetch} "
                f"({fetched_count:,}건 확인)"
            )

        existing_bid_numbers = set(
            BidNotice.objects.values_list("bid_ntce_no", flat=True)
        )
        created_count = 0
        updated_count = 0
        active_count = 0
        review_count = 0
        expired_skipped_count = 0
        now = timezone.now()

        # 이미 저장된 공고는 시간이 지나면 자동으로 마감 상태로 바꾼다.
        BidNotice.objects.filter(
            close_at__lte=now,
            is_active=True,
        ).update(
            deadline_status=BidNotice.DeadlineStatus.EXPIRED,
            is_active=False,
        )

        with transaction.atomic():
            for item in latest_notices.values():
                bid_ntce_no = item["bidNtceNo"]
                bid_ntce_ord = item.get("bidNtceOrd", "000")
                status = item.get("bidNtceSttusNm", "")
                close_at = parse_datetime(
                    item.get("bidClseDate"),
                    item.get("bidClseTm"),
                )
                deadline_status = determine_deadline_status(status, close_at)

                # 서비스 시작 전 이미 끝난 공고는 새로 저장하지 않는다.
                if (
                    deadline_status == BidNotice.DeadlineStatus.EXPIRED
                    and bid_ntce_no not in existing_bid_numbers
                ):
                    expired_skipped_count += 1
                    continue

                # 같은 공고번호의 이전 차수는 추천 후보에서 제외한다.
                BidNotice.objects.filter(
                    bid_ntce_no=bid_ntce_no,
                ).exclude(
                    bid_ntce_ord=bid_ntce_ord,
                ).update(is_active=False)

                _, created = BidNotice.objects.update_or_create(
                    bid_ntce_no=bid_ntce_no,
                    bid_ntce_ord=bid_ntce_ord,
                    defaults=build_notice_defaults(
                        item,
                        status,
                        close_at,
                        deadline_status,
                    ),
                )

                existing_bid_numbers.add(bid_ntce_no)

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                if deadline_status == BidNotice.DeadlineStatus.ACTIVE:
                    active_count += 1
                elif deadline_status == BidNotice.DeadlineStatus.REVIEW:
                    review_count += 1

        self.stdout.write(self.style.SUCCESS("입찰공고 수집이 완료됐습니다."))
        self.stdout.write(f"이번에 확인한 페이지: {pages_to_fetch}페이지")
        self.stdout.write(f"확인한 원본 행: {fetched_count:,}건")
        self.stdout.write(f"최신 공고번호: {len(latest_notices):,}건")
        self.stdout.write(f"유효공고 처리: {active_count:,}건")
        self.stdout.write(f"확인 필요 처리: {review_count:,}건")
        self.stdout.write(f"과거 마감공고 제외: {expired_skipped_count:,}건")
        self.stdout.write(f"새로 저장: {created_count:,}건")
        self.stdout.write(f"기존 업데이트: {updated_count:,}건")
        self.stdout.write(f"현재 DB 전체: {BidNotice.objects.count():,}건")
