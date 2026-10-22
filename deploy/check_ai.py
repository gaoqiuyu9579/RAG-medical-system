"""仅发送合成测试文本，不读写业务数据库或知识库，不输出服务凭证。"""

import json

from flask import Flask

from backend.config.config import Config
from backend.rag.embedding import get_embedding
from backend.rag.llm import get_llm


def main():
    app = Flask(__name__)
    app.config.from_object(Config)
    results = {}
    with app.app_context():
        for name, action in (
            ("embedding", lambda: len(get_embedding().embed_query("系统连通性测试"))),
            ("chat", lambda: bool(get_llm().invoke("连通性测试，请只回复 OK。").content)),
        ):
            try:
                results[name] = {"ok": True, "result": action()}
            except Exception as exc:
                results[name] = {"ok": False, "error_type": type(exc).__name__}
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
