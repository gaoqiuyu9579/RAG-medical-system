"""仅监听本机的独立演示实例：使用合成业务数据和真实外部 AI 客户端。"""

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_app
from backend.config.database import db
from backend.model.user import User
from backend.utils.passwords import hash_password
import backend.rag.vector_store as vectors


def main():
    artifacts = ROOT / ".test-artifacts" / ("review-demo-" + uuid.uuid4().hex)
    artifacts.mkdir(parents=True, exist_ok=True)
    vectors.VECTOR_PATH = str(artifacts / "chroma")
    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (artifacts / "business.sqlite3").as_posix(),
            "SECRET_KEY": "isolated-local-review-demo-key-not-for-deployment",
            "CORS_ORIGINS": [],
        }
    )
    with app.app_context():
        if User.query.filter_by(username="reviewer").first() is None:
            db.session.add(
                User(
                    username="reviewer",
                    password=hash_password("ReviewDemo2026!"),
                    real_name="评审演示账号",
                    role="admin",
                    status=1,
                )
            )
            db.session.commit()
    print(
        json.dumps(
            {
                "demo": "http://127.0.0.1:5502",
                "data": "synthetic-only",
                "ai": "real-configured-clients",
            }
        ),
        flush=True,
    )
    from waitress import serve

    serve(app, host="127.0.0.1", port=5502, threads=4)


if __name__ == "__main__":
    main()
