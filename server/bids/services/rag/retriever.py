from chromadb.config import Settings
from langchain_chroma import Chroma  # 저장된 벡터 DB 불러오기
from langchain_openai import OpenAIEmbeddings  # 질문을 벡터로 변환
from ..llm import cloud_options
from .keyword_store import load_keyword_documents, search_keyword_documents, search_mode

from .vector_store import (
    EMBEDDING_MODEL,
    get_bid_db_path,
    get_collection_name,
    normalize_l2_relevance_score,
)


MAX_SEARCH_CANDIDATES = 30  # 먼저 비교할 관련 Chunk 후보 수
MIN_RELEVANCE_SCORE = 0.2  # 이 점수 이상인 Chunk만 최종 문맥으로 사용
MIN_SEARCH_RESULTS = 5  # 점수 기준이 너무 엄격해도 최소한 확보할 Chunk 수


def get_bid_vector_store(bid_ntce_no):  # 공고번호 전용 Chroma DB를 불러오는 함수
    db_path = get_bid_db_path(bid_ntce_no)  # 공고별 DB 경로

    if not db_path.exists():  # 아직 처리하지 않은 공고인지 확인
        raise ValueError("해당 공고의 Chroma DB가 없습니다.")

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, **cloud_options())

    return Chroma(
        client_settings=Settings(anonymized_telemetry=False),
        collection_name=get_collection_name(bid_ntce_no),  # 해당 공고 컬렉션 선택
        persist_directory=str(db_path),  # 저장된 Chroma 연결
        embedding_function=embeddings,  # 질문과 문서 벡터 비교에 사용
        relevance_score_fn=normalize_l2_relevance_score,
    )



def get_bid_document_data(bid_ntce_no):
    if search_mode() == "keyword":
        documents = load_keyword_documents(bid_ntce_no)
        return {"documents": [d.page_content for d in documents], "metadatas": [d.metadata for d in documents]}
    return get_bid_vector_store(bid_ntce_no).get(include=["documents", "metadatas"])


def search_bid_documents(bid_ntce_no, question):  # 질문과 관련된 Chunk를 동적으로 고르는 함수
    if search_mode() == "keyword":
        return search_keyword_documents(bid_ntce_no, question, MAX_SEARCH_CANDIDATES)
    vector_store = get_bid_vector_store(bid_ntce_no)
    stored_chunk_count = vector_store._collection.count()  # 공고에 저장된 전체 Chunk 수
    candidate_count = min(stored_chunk_count, MAX_SEARCH_CANDIDATES)

    if candidate_count == 0:
        raise ValueError("해당 공고에 저장된 Chunk가 없습니다.")

    results = vector_store.similarity_search_with_relevance_scores(
        question,
        k=candidate_count,
    )  # 후보 Chunk와 질문의 관련도 점수를 함께 검색

    relevant_documents = [
        document
        for document, score in results
        if score >= MIN_RELEVANCE_SCORE
    ]  # 관련도 기준을 통과한 Chunk는 개수 제한 없이 선택

    if len(relevant_documents) < MIN_SEARCH_RESULTS:
        return [
            document
            for document, _score in results[:MIN_SEARCH_RESULTS]
        ]  # 결과가 너무 적으면 상위 5개까지 보완

    return relevant_documents
