"""真实本地 Chroma 存取与检索回归，不调用外部模型。"""

import hashlib
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from backend.app import create_app
from backend.config.database import db
import backend.rag.vector_store as vectors
from backend.rag.qa_chain import ask_medical_question
from backend.utils.secrets import signing_key


class LocalEmbedding(Embeddings):
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        return [value / 255.0 for value in hashlib.sha256(text.encode("utf-8")).digest()[:16]]


class RagTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(__file__).resolve().parents[1] / ".test-artifacts" / ("rag-" + uuid.uuid4().hex)
        self.folder.mkdir(parents=True)
        self.path_patch = patch.object(vectors, "VECTOR_PATH", str(self.folder / "chroma"))
        self.path_patch.start()
        self.embedding_patch = patch.object(vectors, "get_embedding", return_value=LocalEmbedding())
        self.embedding = self.embedding_patch.start()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "rag-test-secret-32-characters-minimum",
                               "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()
        self.embedding_patch.stop()
        self.path_patch.stop()

    def test_upload_persists_and_repeated_upload_does_not_duplicate(self):
        first = vectors.create_vector_store("测试资料 MED-DEMO-01", "test.txt")
        second = vectors.create_vector_store("测试资料 MED-DEMO-01", "test.txt")
        self.assertEqual(first, {"added": 1, "total": 1})
        self.assertEqual(second, {"added": 0, "total": 1})
        self.assertEqual(vectors.knowledge_status(), {"ready": True, "chunks": 1})
        results = vectors.load_vector_store().similarity_search("MED-DEMO-01", k=3)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata["source"], "test.txt")

    def test_failed_embedding_does_not_write_partial_documents(self):
        self.embedding.return_value.embed_documents = lambda _: (_ for _ in ()).throw(RuntimeError("test failure"))
        with self.assertRaises(RuntimeError):
            vectors.create_vector_store("较长的测试资料。" * 200)
        self.assertEqual(vectors.knowledge_status()["chunks"], 0)
        self.assertIsNone(vectors.load_vector_store())

    def test_empty_existing_collection_does_not_invoke_embedding(self):
        vectors.vector_client().get_or_create_collection(vectors.COLLECTION_NAME, embedding_function=None)
        self.embedding.reset_mock()
        self.assertIsNone(vectors.load_vector_store())
        self.embedding.assert_not_called()

    def test_existing_legacy_collection_can_be_loaded(self):
        collection = vectors.vector_client().get_or_create_collection("langchain", embedding_function=None)
        collection.add(ids=["legacy-uuid"], documents=["既有资料"],
                       embeddings=[LocalEmbedding().embed_query("既有资料")])
        self.assertEqual(vectors.load_vector_store().similarity_search("既有资料", k=1)[0].page_content, "既有资料")

    def test_question_uses_retrieved_context_and_returns_sources(self):
        vectors.create_vector_store("演示资料编号 MED-DEMO-01", "source.txt")
        prompts = []
        def answer(prompt):
            prompts.append(prompt.to_string())
            return AIMessage(content="编号为 MED-DEMO-01")
        with patch("backend.rag.qa_chain.get_llm", return_value=RunnableLambda(answer)):
            result = ask_medical_question("编号是什么？")
        self.assertEqual(result["sources"], ["source.txt"])
        self.assertIn("MED-DEMO-01", prompts[0])
        self.assertIn("编号是什么", prompts[0])

    def test_random_signing_key_is_persisted_and_placeholder_is_not_used(self):
        filename = self.folder / "jwt.secret"
        first = signing_key("smart-medical-secret", filename)
        second = signing_key("", filename)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 32)
        self.assertNotEqual(first, "smart-medical-secret")


if __name__ == "__main__":
    unittest.main()
