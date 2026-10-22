"""真实 AI 检索链联调，仅在 /tmp 临时知识库写入合成资料。"""

import json
import tempfile
from unittest.mock import patch

from flask import Flask

from backend.config.config import Config
from backend.rag.qa_chain import ask_medical_question
import backend.rag.vector_store as vectors


def main():
    app = Flask(__name__)
    app.config.from_object(Config)
    with tempfile.TemporaryDirectory(prefix="medical_rag_live_") as directory:
        with app.app_context(), patch.object(vectors, "VECTOR_PATH", directory):
            created = vectors.create_vector_store("连通性测试资料：测试编号为 MED-CONNECT-2026。此资料不含患者信息。", "合成连通测试")
            result = ask_medical_question("连通性测试资料的测试编号是什么？")
            assert created["added"] == 1
            assert "MED-CONNECT-2026" in result["answer"]
            assert result["sources"] == ["合成连通测试"]
            print(json.dumps({"live_rag": "passed", "synthetic_chunks": 1, "answer_and_source_verified": True}))


if __name__ == "__main__":
    main()
