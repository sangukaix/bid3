import hashlib

from django.utils import timezone

from .company_knowledge import (
    _extract_batch_knowledge,
    _normalize_tags,
    build_knowledge_batches,
)
from .rag.extract_document import extract_document


MAX_REFERENCE_CONTEXT_CHARS = 60000


def _file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_project_reference_knowledge(document):
    """유사 제안서에서 이번 프로젝트에 재사용할 수 있는 근거만 추출합니다."""

    extraction = extract_document(document.file.path)
    if not extraction.documents:
        reason = (
            extraction.failed_files[0]["reason"]
            if extraction.failed_files
            else "텍스트가 없습니다."
        )
        raise ValueError(f"유사 제안서를 읽지 못했습니다: {reason}")

    batches, used_chars, total_chars = build_knowledge_batches(
        extraction.documents,
        document.original_name,
    )
    items = []
    duplicate_keys = set()
    for batch in batches:
        result = _extract_batch_knowledge(batch.context)
        for item in result.items:
            sources = [
                batch.sources[number]
                for number in item.source_numbers
                if number in batch.sources
            ]
            if not sources:
                continue
            title = item.title.strip()
            content = item.content.strip()
            duplicate_key = (item.category, title.casefold(), content.casefold())
            if duplicate_key in duplicate_keys:
                continue
            duplicate_keys.add(duplicate_key)
            items.append(
                {
                    "category": item.category,
                    "title": title,
                    "content": content,
                    "source_locations": list(
                        dict.fromkeys(source.location for source in sources)
                    ),
                    "evidence_excerpt": "\n\n".join(
                        source.excerpt for source in sources[:2]
                    )[:1500],
                    "tags": _normalize_tags(item.tags),
                }
            )

    if not items:
        raise ValueError("유사 제안서에서 참고할 내용을 찾지 못했습니다.")
    return {
        "items": items,
        "processed_files": extraction.processed_files,
        "failed_files": extraction.failed_files,
        "batch_count": len(batches),
        "used_chars": used_chars,
        "total_chars": total_chars,
    }


def prepare_project_reference(document, force=False):
    """같은 유사 제안서는 다시 OpenAI로 분석하지 않고 저장 결과를 재사용합니다."""

    current_hash = _file_hash(document.file.path)
    if (
        document.extracted_knowledge
        and document.content_hash == current_hash
        and not force
    ):
        return {
            "items": document.extracted_knowledge,
            "reused": True,
            "item_count": len(document.extracted_knowledge),
        }

    result = extract_project_reference_knowledge(document)
    document.extracted_knowledge = result["items"]
    document.content_hash = current_hash
    document.processed_at = timezone.now()
    document.save(
        update_fields=("extracted_knowledge", "content_hash", "processed_at")
    )
    return {
        **result,
        "reused": False,
        "item_count": len(result["items"]),
    }


def build_project_reference_context(saved_bid, max_chars=MAX_REFERENCE_CONTEXT_CHARS):
    """현재 프로젝트의 유사 제안서만 제안서 생성용 문맥으로 만듭니다."""

    parts = []
    used_chars = 0
    processed_files = []
    reused_files = []
    failed_files = []
    item_count = 0

    for document in saved_bid.reference_documents.all().order_by("id"):
        try:
            result = prepare_project_reference(document)
        except (OSError, ValueError) as error:
            failed_files.append(
                {"file_name": document.original_name, "reason": str(error)}
            )
            continue

        item_count += result["item_count"]
        if result["reused"]:
            reused_files.append(document.original_name)
        else:
            processed_files.append(document.original_name)

        for item in result["items"]:
            locations = ", ".join(item.get("source_locations", [])) or "위치 정보 없음"
            part = (
                f"[{document.original_name} | {locations}]\n"
                f"{item.get('title', '참고 내용')}: {item.get('content', '')}"
            )
            remaining = max_chars - used_chars
            if remaining <= 0:
                break
            parts.append(part[:remaining])
            used_chars += min(len(part), remaining)

    context = "\n\n".join(parts)
    if not context:
        context = "현재 프로젝트에 등록된 유사 제안서 참고 내용이 없습니다."
    return context, {
        "item_count": item_count,
        "processed_files": processed_files,
        "reused_files": reused_files,
        "failed_files": failed_files,
        "used_chars": used_chars,
    }
