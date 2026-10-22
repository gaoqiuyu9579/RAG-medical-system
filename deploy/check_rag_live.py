"""真实 AI 检索链联调，在子进程退出后清理隔离的临时知识库。"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from backend.config.config import Config
from backend.rag.qa_chain import ask_medical_question
import backend.rag.vector_store as vectors


def check(directory):
    app = Flask(__name__)
    app.config.from_object(Config)
    with app.app_context(), patch.object(vectors, "VECTOR_PATH", directory):
        created = vectors.create_vector_store(
            "连通性测试资料：测试编号为 MED-CONNECT-2026。此资料不含患者信息。", "合成连通测试"
        )
        result = ask_medical_question("连通性测试资料的测试编号是什么？")
        assert created["added"] == 1
        assert "MED-CONNECT-2026" in result["answer"]
        assert result["sources"] == ["合成连通测试"]
        print(
            json.dumps(
                {"live_rag": "passed", "synthetic_chunks": 1, "answer_and_source_verified": True}
            )
        )


def main():
    # Chroma 在 Windows 会持有 SQLite 句柄。由子进程执行联调，退出释放句柄后
    # 再由父进程删除临时目录，避免断言已通过但清理阶段报 WinError 32。
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        check(sys.argv[2])
        return
    with tempfile.TemporaryDirectory(prefix="medical_rag_live_") as directory:
        subprocess.run(
            [sys.executable, "-m", "deploy.check_rag_live", "--worker", directory],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
        )


if __name__ == "__main__":
    main()
