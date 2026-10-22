"""仅供浏览器测试的隔离服务，使用合成资料和本地模型替身。"""

import hashlib
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from backend.app import create_app
from backend.config.database import db
from backend.model.user import User
from backend.utils.passwords import hash_password
import backend.rag.vector_store as vectors
import backend.rag.qa_chain as qa


class TestEmbedding(Embeddings):
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        return [value / 255.0 for value in hashlib.sha256(text.encode("utf-8")).digest()[:16]]


artifacts = ROOT / ".test-artifacts" / ("e2e-" + uuid.uuid4().hex)
artifacts.mkdir(parents=True, exist_ok=False)
vectors.VECTOR_PATH = str(artifacts / "chroma")
vectors.get_embedding = lambda: TestEmbedding()
qa.get_llm = lambda: RunnableLambda(lambda _: AIMessage(content="演示资料编号为 MED-DEMO-01。"))

app = create_app({
    "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (artifacts / "business.sqlite3").as_posix(),
    "SECRET_KEY": "isolated-browser-test-key-not-for-production",
    "DASHSCOPE_API_KEY": "",
    "DEEPSEEK_API_KEY": "",
})


def reset():
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        db.session.add(User(username="e2e-admin", password=hash_password("E2ePassword123"),
                            role="admin", status=1, real_name="测试管理员"))
        db.session.commit()
        collection = vectors.existing_collection()
        if collection is not None:
            ids = collection.get(include=[])["ids"]
            if ids:
                collection.delete(ids=ids)


@app.post("/__test__/reset")
def reset_endpoint():
    reset()
    return {"ok": True}


if __name__ == "__main__":
    reset()
    app.run(host="127.0.0.1", port=5501, debug=False, threaded=False)
