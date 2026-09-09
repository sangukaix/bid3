import base64

from .llm import cloud_client, model_selection
from .local_vision import extract_local_registration
from pydantic import BaseModel


MODEL = "gpt-4o-mini"  # 단순 문서 추출에는 기존 저비용 모델 사용
MAX_OUTPUT_TOKENS = 500  # 네 가지 기본정보만 받아 비용을 제한
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = 5 * 1024 * 1024


class BusinessRegistrationData(BaseModel):
    company_name: str | None = None
    business_registration_number: str | None = None
    representative_name: str | None = None
    address: str | None = None


INSTRUCTIONS = """
첨부 문서는 대한민국 사업자등록증입니다.
문서에서 직접 확인되는 값만 다음 필드에 옮기세요.
- company_name: 상호(법인명)
- business_registration_number: 등록번호
- representative_name: 성명(대표자)
- address: 사업장 소재지

중요:
- 문서에 없거나 글자가 불명확한 값은 반드시 null로 반환합니다.
- 추측, 보완, 검색, 형식 변경을 하지 않습니다.
- 전화번호, 이메일, 개업연월일, 업태, 종목은 반환하지 않습니다.
"""


def extract_business_registration(uploaded_file):
    """사업자등록증에서 문서에 명시된 기본정보만 구조화해 반환합니다."""

    if uploaded_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("PDF, JPG, PNG 파일만 사용할 수 있습니다.")
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValueError("파일 크기는 5MB 이하여야 합니다.")

    file_bytes = uploaded_file.read()
    if model_selection("BUSINESS_REGISTRATION", MODEL)[0] == "ollama":
        return extract_local_registration(file_bytes, uploaded_file.content_type, BusinessRegistrationData, INSTRUCTIONS)
    client = cloud_client(timeout=40.0, max_retries=0)
    temporary_file_id = None

    if uploaded_file.content_type == "application/pdf":
        temporary_file = client.files.create(
            file=(uploaded_file.name, file_bytes, uploaded_file.content_type),
            purpose="user_data",
        )
        temporary_file_id = temporary_file.id
        document_input = {"type": "input_file", "file_id": temporary_file_id}
    else:
        encoded_file = base64.b64encode(file_bytes).decode("ascii")
        document_input = {
            "type": "input_image",
            "image_url": f"data:{uploaded_file.content_type};base64,{encoded_file}",
            "detail": "low",
        }

    try:
        response = client.responses.parse(
            model=MODEL,
            instructions=INSTRUCTIONS,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "사업자등록증의 기본정보를 추출하세요."},
                        document_input,
                    ],
                }
            ],
            text_format=BusinessRegistrationData,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0,
        )
        result = response.output_parsed
        if result is None:
            raise ValueError("사업자등록증에서 기본정보를 확인하지 못했습니다.")
        return result.model_dump()
    finally:
        if temporary_file_id:
            client.files.delete(temporary_file_id)
