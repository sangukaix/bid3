from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests # 다른 서버에 HTTP 요청을 보내는 패키지

from django.conf import settings # settings.py에 등록한 설정값을 가져옴.
from django.core.exceptions import ImproperlyConfigured

SERVICE_URL = (
    "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/"
    "getDataSetOpnStdBidPblancInfo"
)  # 공공데이터 개방표준 방식의 나라장터 입찰공고 조회 주소


def fetch_bid_notices(
    page_no=1,
    num_of_rows=10,
    start_at=None,
    end_at=None,
): #나라장터 입찰공고를 가져오는 함수
    if not settings.G2B_API_KEY:
        raise ImproperlyConfigured("G2B_API_KEY가 설정되지 않았습니다.")

    if page_no < 1:
        raise ValueError("page_no는 1 이상이어야 합니다.")

    if not 1 <= num_of_rows <= 999:
        raise ValueError("num_of_rows는 1부터 999까지 가능합니다.")

    end_at = end_at or datetime.now(ZoneInfo("Asia/Seoul"))
    start_at = start_at or end_at - timedelta(days=10)

    params = {
        "serviceKey" : settings.G2B_API_KEY, # .env에서 읽은 인증키
        "pageNo": page_no, #조회할 페이지 번호
        "numOfRows": num_of_rows,
        "type": "json",
        "bidNtceBgnDt": start_at.strftime("%Y%m%d%H%M"),
        "bidNtceEndDt": end_at.strftime("%Y%m%d%H%M"),
    }

    response = requests.get( #나라장터에 겟방식으로 정보를 요청하고 제이슨으로 받음
        SERVICE_URL,
        params=params,
        timeout=30, #대량 응답을 고려해 최대 30초 대기
    )

    response.raise_for_status() #400, 500 같은 http 오류 있으면 에러 발생

    return response.json()
