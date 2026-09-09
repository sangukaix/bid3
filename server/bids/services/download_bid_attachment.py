from pathlib import Path

import requests

from django.conf import settings


MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024  # 첨부파일 한 개의 다운로드 최대 크기


def download_bid_attachment(bid_ntce_no, attachment):
    """첨부파일 한 개를 공고별 폴더에 다운로드합니다."""
    filename = Path(attachment.get("filename", "")).name
    download_url = attachment.get("download_url", "")

    if not filename or not download_url:
        raise ValueError("첨부파일 이름과 다운로드 주소가 필요합니다.")

    response = requests.get(download_url, timeout=60, stream=True)
    response.raise_for_status()

    folder = Path(settings.MEDIA_ROOT) / "bid_documents" / bid_ntce_no
    folder.mkdir(parents=True, exist_ok=True)  # 공고번호별 저장 폴더가 없으면 생성

    file_path = folder / filename
    downloaded_bytes = 0

    with file_path.open("wb") as saved_file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue

            downloaded_bytes += len(chunk)
            if downloaded_bytes > MAX_ATTACHMENT_BYTES:
                saved_file.close()
                file_path.unlink(missing_ok=True)
                raise ValueError("첨부파일 크기가 100MB를 초과했습니다.")

            saved_file.write(chunk)

    if downloaded_bytes == 0:
        file_path.unlink(missing_ok=True)
        raise ValueError("다운로드한 첨부파일이 비어 있습니다.")

    return file_path
