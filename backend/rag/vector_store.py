"""持久化知识库，重复文本去重，先完成向量化再写入。"""

import hashlib
import os
import threading

import chromadb
from chromadb.config import Settings
from chromadb.errors import InvalidCollectionException
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.rag.embedding import get_embedding

VECTOR_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
COLLECTION_NAME = "langchain"  # 保留旧版集合名称，兼容已有知识库。
_WRITE_LOCK = threading.RLock()


class VectorStore:
    """仅使用 Chroma 本地公开接口，避免依赖已弃用的社区适配器。"""

    def __init__(self, collection, embedding):
        self.collection = collection
        self.embedding = embedding

    def similarity_search(self, question, k=3):
        count = self.collection.count()
        if not count:
            return []
        result = self.collection.query(
            query_embeddings=[self.embedding.embed_query(question)],
            n_results=min(k, count),
            include=["documents", "metadatas"],
        )
        return [
            Document(page_content=text, metadata=metadata or {})
            for text, metadata in zip(result["documents"][0], result["metadatas"][0])
        ]


def vector_client():
    return chromadb.PersistentClient(
        path=VECTOR_PATH, settings=Settings(anonymized_telemetry=False)
    )


def existing_collection():
    if not os.path.isfile(os.path.join(VECTOR_PATH, "chroma.sqlite3")):
        return None
    try:
        return vector_client().get_collection(COLLECTION_NAME, embedding_function=None)
    except InvalidCollectionException:
        return None


def knowledge_status():
    with _WRITE_LOCK:
        collection = existing_collection()
        count = collection.count() if collection is not None else 0
        metadata = collection.get(include=["metadatas"])["metadatas"] if count else []
        documents = len(
            {
                (item or {}).get("document_id", (item or {}).get("source", "既有知识库"))
                for item in metadata
            }
        )
        if count and not documents:
            documents = 1
        return {"ready": count > 0, "chunks": count, "documents": documents}


def create_vector_store(text, source="粘贴文本"):
    for event in stream_vector_store(text, source):
        if event["type"] == "done":
            return event["result"]


def stream_vector_store(text, source="粘贴文本"):
    yield {"type": "progress", "stage": "parsing", "message": "文档解析中 · 正在分块"}
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    documents = splitter.split_documents([Document(page_content=text)])
    # 同次上传中的重复片段也需要合并。
    unique = {
        hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest(): doc.page_content
        for doc in documents
        if doc.page_content.strip()
    }
    yield {
        "type": "progress",
        "stage": "vectorizing",
        "message": "向量化中 · 正在生成并保存知识向量",
    }
    with _WRITE_LOCK:
        # 配置检查先于建库，空目录仍然可以正确返回“知识库为空”。
        embedding = get_embedding()
        collection = vector_client().get_or_create_collection(
            COLLECTION_NAME, embedding_function=None
        )
        existing = set(collection.get(ids=list(unique), include=[])["ids"]) if unique else set()
        ids = [identifier for identifier in unique if identifier not in existing]
        if not ids:
            yield {"type": "done", "result": {"added": 0, "total": collection.count()}}
            return
        texts = [unique[identifier] for identifier in ids]
    # 网络调用不占用读写锁，状态查询和已有知识检索仍可响应。
    vectors = embedding.embed_documents(texts)
    document_id = hashlib.sha256((source + "\n" + text).encode("utf-8")).hexdigest()
    with _WRITE_LOCK:
        # 并发导入可能已写入相同片段，写入前重新检查。
        existing = set(collection.get(ids=ids, include=[])["ids"])
        remaining = [
            (identifier, content, vector, index)
            for index, (identifier, content, vector) in enumerate(zip(ids, texts, vectors), 1)
            if identifier not in existing
        ]
        if not remaining:
            yield {"type": "done", "result": {"added": 0, "total": collection.count()}}
            return
        collection.add(
            ids=[item[0] for item in remaining],
            documents=[item[1] for item in remaining],
            embeddings=[item[2] for item in remaining],
            metadatas=[
                {"source": source, "document_id": document_id, "chunk": item[3]}
                for item in remaining
            ],
        )
        yield {"type": "done", "result": {"added": len(remaining), "total": collection.count()}}


def load_vector_store():
    with _WRITE_LOCK:
        collection = existing_collection()
        if collection is None or collection.count() == 0:
            return None
        return VectorStore(collection, get_embedding())
