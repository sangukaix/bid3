"""Local-only image/PDF extraction for business registration uploads."""
import base64
from io import BytesIO
import os
import requests
from PIL import Image, ImageOps
import pypdfium2 as pdfium
from langchain_core.messages import HumanMessage, SystemMessage
from .llm import LOCAL_MODEL_LOCK, build_text_model, ollama_schema


def _image_bytes(image):
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((2000, 2000))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def extract_local_registration(content, content_type, schema, instructions):
    images, texts = [], []
    if content_type == "application/pdf":
        try:
            with pdfium.PdfDocument(content) as document:
                if not 1 <= len(document) <= 5:
                    raise ValueError("사업자등록증 PDF는 1~5페이지여야 합니다.")
                for index in range(len(document)):
                    page = document[index]
                    textpage = page.get_textpage()
                    text = textpage.get_text_range().strip()
                    textpage.close()
                    texts.append(text)
                    width, height = page.get_size()
                    bitmap = page.render(scale=min(2, 2000 / max(width, height)))
                    pil_image = bitmap.to_pil()
                    images.append(_image_bytes(pil_image))
                    pil_image.close(); bitmap.close(); page.close()
        except ValueError:
            raise
        except Exception as error:
            raise ValueError("PDF를 읽을 수 없습니다. 암호 또는 파일 손상을 확인하세요.") from error
        if all(len(t) > 40 for t in texts):
            # Real PDF text avoids unnecessary vision inference.
            result = build_text_model("BUSINESS_REGISTRATION", "gpt-4o-mini", 768).with_structured_output(schema).invoke([
                SystemMessage(content=instructions),
                HumanMessage(content="\n\n".join(f"[페이지 {i}]\n{t}" for i,t in enumerate(texts,1))),
            ])
            return result.model_dump()
    else:
        try:
            with Image.open(BytesIO(content)) as image:
                if image.width * image.height > 25000000:
                    raise ValueError("이미지는 2,500만 픽셀 이하여야 합니다.")
                images.append(_image_bytes(image))
        except ValueError:
            raise
        except Exception as error:
            raise ValueError("이미지 파일을 읽을 수 없습니다.") from error
    # One page at a time keeps vision memory bounded. Conflicting values stay null.
    results = []
    for image in images:
        payload = {
            "model": os.getenv("LOCAL_VISION_MODEL", "gemma4:26b"),
            "messages": [{"role": "user", "content": instructions,
                          "images": [base64.b64encode(image).decode("ascii")]}],
            "stream": False, "think": False,
            "format": ollama_schema(schema.model_json_schema()),
            "keep_alive": os.getenv("LOCAL_LLM_KEEP_ALIVE", "0"),
            "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 768},
        }
        with LOCAL_MODEL_LOCK:
            response = requests.post(
                os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat",
                json=payload, timeout=(10, float(os.getenv("LOCAL_VISION_TIMEOUT", "300"))))
        response.raise_for_status()
        data = response.json()
        if data.get("done_reason") == "length":
            raise ValueError("사업자등록증 추출 출력이 잘렸습니다.")
        results.append(schema.model_validate_json(data["message"]["content"]).model_dump())
    merged = {}
    for field in schema.model_fields:
        values = {r[field].strip() for r in results if isinstance(r[field], str) and r[field].strip()}
        merged[field] = next(iter(values)) if len(values) == 1 else None
    return schema.model_validate(merged).model_dump()
