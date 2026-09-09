"""Optional local text index and BM25-style keyword retrieval, without embeddings."""

from collections import Counter
import json
from math import log
import os
import re
from uuid import uuid4

from langchain_core.documents import Document
from .vector_store import get_bid_db_path, get_collection_name


def search_mode():
    from ..llm import local_only
    if local_only():
        return "keyword"
    mode = os.getenv("RAG_SEARCH_MODE", "vector").strip().lower()
    if mode not in {"vector", "keyword"}:
        raise ValueError("RAG_SEARCH_MODE는 vector 또는 keyword여야 합니다.")
    return mode


def save_keyword_documents(bid_ntce_no, documents):
    root = get_bid_db_path(bid_ntce_no)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "text_chunks.json"
    temporary = path.with_name(f".text_chunks-{uuid4().hex}.json")
    temporary.write_text(json.dumps([
        {"page_content": d.page_content, "metadata": d.metadata}
        for d in documents
    ], ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def load_keyword_documents(bid_ntce_no):
    root = get_bid_db_path(bid_ntce_no)
    path = root / "text_chunks.json"
    if path.exists():
        records = json.loads(path.read_text(encoding="utf-8"))
        return [Document(page_content=r["page_content"], metadata=r["metadata"]) for r in records]
    if not (root / "chroma.sqlite3").exists():
        return []
    # Reading stored documents never requires the embedding model or an API key.
    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(str(root), settings=Settings(anonymized_telemetry=False))
    collection = client.get_collection(get_collection_name(bid_ntce_no), embedding_function=None)
    records = collection.get(include=["documents", "metadatas"])
    documents = [
        Document(page_content=content, metadata=metadata or {})
        for content, metadata in zip(records["documents"], records["metadatas"])
        if content
    ]
    if documents:
        save_keyword_documents(bid_ntce_no, documents)
    return documents


def _terms(text):
    terms = re.findall(r"[a-z0-9]+|[가-힣]+", text.lower())
    # Korean bigrams help match words with different particles; no model download.
    return terms + [
        word[i:i + 2] for word in terms if re.fullmatch(r"[가-힣]{3,}", word)
        for i in range(len(word) - 1)
    ]


def search_keyword_documents(bid_ntce_no, question, limit=30):
    documents = load_keyword_documents(bid_ntce_no)
    if not documents:
        raise ValueError("검색할 공고 문서가 없습니다.")
    query_terms = set(_terms(question))
    counters = [Counter(_terms(d.page_content)) for d in documents]
    lengths = [sum(c.values()) for c in counters]
    average = max(sum(lengths) / len(lengths), 1)
    frequency = {term: sum(term in c for c in counters) for term in query_terms}
    scores = []
    for index, (counts, length) in enumerate(zip(counters, lengths)):
        score = 0.0
        for term in query_terms:
            count = counts[term]
            if count:
                idf = log(1 + (len(documents) - frequency[term] + 0.5) / (frequency[term] + 0.5))
                score += idf * count * 2.2 / (count + 1.2 * (0.25 + 0.75 * length / average))
        scores.append((score, index))
    scores.sort(key=lambda item: (-item[0], item[1]))
    selected = [index for score, index in scores if score > 0][:limit]
    if len(selected) < min(5, len(documents)):
        selected = [index for _, index in scores[:min(5, len(documents))]]
    return [documents[index] for index in selected]
