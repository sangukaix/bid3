import requests

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"

# 업무구분에 맞는 나라장터 상세조회 기능을 선택합니다.
OPERATION_BY_BUSINESS_TYPE = {
    "물품": "getBidPblancListInfoThng",
    "용역": "getBidPblancListInfoServc",
    "공사": "getBidPblancListInfoCnstwk",
    "외자": "getBidPblancListInfoFrgcpt",
    "기타": "getBidPblancListInfoEtc",
}


def fetch_bid_attachments(bid_ntce_no, business_type, bid_ntce_ord=None):
    """공고번호로 나라장터 첨부파일 이름과 다운로드 주소를 가져옵니다."""
    if not settings.G2B_API_KEY:
        raise ImproperlyConfigured("G2B_API_KEY가 설정되지 않았습니다.")

    operation = OPERATION_BY_BUSINESS_TYPE.get(business_type)
    if operation is None:
        raise ValueError("지원하지 않는 업무구분입니다.")

    params = {
        "serviceKey": settings.G2B_API_KEY,  # .env에 저장된 나라장터 인증키
        "pageNo": 1,
        "numOfRows": 10,
        "type": "json",
        "inqryDiv": 2,  # 날짜가 아니라 공고번호 한 건으로 조회
        "bidNtceNo": bid_ntce_no,
    }
    response = requests.get(
        f"{BASE_URL}/{operation}",
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        raise RuntimeError(header.get("resultMsg") or "나라장터 API 요청에 실패했습니다.")

    items = data.get("response", {}).get("body", {}).get("items") or []
    if bid_ntce_ord is not None:
        items = [item for item in items if item.get("bidNtceOrd") == bid_ntce_ord]

    if not items:
        return []

    notice = max(items, key=lambda item: int(item.get("bidNtceOrd") or 0))
    attachments = []

    for number in range(1, 11):  # 나라장터가 제공하는 첨부파일 1번부터 10번까지 확인
        filename = notice.get(f"ntceSpecFileNm{number}")
        download_url = notice.get(f"ntceSpecDocUrl{number}")

        if filename and download_url:
            attachments.append(
                {
                    "filename": filename,
                    "download_url": download_url,
                }
            )

    return attachments
