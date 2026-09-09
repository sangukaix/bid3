from langchain_text_splitters import RecursiveCharacterTextSplitter #긴문서 분할도구

def split_bid_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100, #겹침
    )

    chunks = splitter.split_documents(documents) #페이지 정보  유지하며 문서 분할
    return chunks
