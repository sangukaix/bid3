from django.core.management.base import BaseCommand

from bids.models import CompanyProfile
from bids.services.recommendation import match_user_recommendations


class Command(BaseCommand):
    help = "회사 조건과 공고를 비교해 회원별 추천 공고를 저장합니다."

    def handle(self, *args, **options):
        checked = 0
        created = 0
        updated = 0

        for profile in CompanyProfile.objects.select_related("user"):
            result = match_user_recommendations(profile.user)
            checked += result["checked"]
            created += result["created"]
            updated += result["updated"]

        self.stdout.write(self.style.SUCCESS("추천 공고 매칭이 완료됐습니다."))
        self.stdout.write(f"확인한 후보: {checked:,}건")
        self.stdout.write(f"새 추천: {created:,}건")
        self.stdout.write(f"기존 추천 갱신: {updated:,}건")
