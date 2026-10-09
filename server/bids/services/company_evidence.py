"""Human-reviewed company knowledge, bound to its current source and text."""
from hashlib import sha256
import json

from django.utils import timezone


def evidence_fingerprint(item, source_cache=None):
    cache = source_cache if source_cache is not None else {}
    if item.source_document_id:
        document = item.source_document
        if document.user_id != item.user_id:
            return ''
        key = ('document', document.pk)
        if key not in cache:
            try:
                digest = sha256()
                with document.file.open('rb') as source:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        digest.update(block)
                cache[key] = digest.hexdigest()
            except OSError:
                cache[key] = ''
        source_hash = cache[key]
    elif item.source_website_page_id:
        page = item.source_website_page
        if page.user_id != item.user_id:
            return ''
        key = ('website', page.pk)
        source_hash = sha256((page.url + '\n' + page.extracted_text).encode()).hexdigest()
    else:
        return ''
    if not source_hash:
        return ''
    payload = [key, source_hash, item.category, item.title, item.content,
               item.source_locations, item.evidence_excerpt]
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def effective_review_status(item, source_cache=None):
    if item.review_status != 'approved':
        return item.review_status
    if item.valid_until and item.valid_until < timezone.localdate():
        return 'expired'
    if not item.reviewed_by_id or not item.reviewed_at or not item.review_fingerprint:
        return 'changed'
    fingerprint = evidence_fingerprint(item, source_cache)
    if not fingerprint or fingerprint != item.review_fingerprint:
        return 'changed'
    return 'approved'


def serialize_evidence(item, source_cache=None):
    document = item.source_document
    page = item.source_website_page
    return {'id':item.pk, 'category':item.category, 'category_label':item.get_category_display(),
        'title':item.title, 'content':item.content, 'source_locations':item.source_locations,
        'evidence_excerpt':item.evidence_excerpt,
        'source_document_id':item.source_document_id, 'source_name':document.original_name if document else page.title if page else '',
        'source_url':page.url if page else '', 'review_status':item.review_status,
        'effective_status':effective_review_status(item, source_cache),
        'reviewed_by':item.reviewed_by.get_username() if item.reviewed_by else '',
        'reviewed_at':item.reviewed_at, 'valid_until':item.valid_until,
        'review_note':item.review_note, 'updated_at':item.updated_at}
