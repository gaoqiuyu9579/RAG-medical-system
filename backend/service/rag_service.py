"""RAG 业务入口。"""

from backend.rag.qa_chain import ask_medical_question
from backend.rag.vector_store import create_vector_store, knowledge_status


class RagService:
    @staticmethod
    def upload_text(text, source="粘贴文本"):
        return create_vector_store(text, source)

    @staticmethod
    def chat(question):
        return ask_medical_question(question)

    @staticmethod
    def status():
        return knowledge_status()
