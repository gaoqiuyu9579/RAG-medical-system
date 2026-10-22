"""Flask 应用工厂与本机启动入口。导入模块不会连接业务数据库。"""

import hmac
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
for directory in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if directory not in sys.path:
        sys.path.insert(0, directory)

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from backend.config.config import Config
from backend.config.database import db
from backend.config.schema import ensure_constraints
from backend.controller.medical_controller import medical_bp
from backend.controller.patient_controller import patient_bp
from backend.controller.rag_controller import rag_bp
from backend.controller.user_controller import user_bp
from backend.model.user import User
from backend.utils.jwt_util import password_version, verify_token
from backend.utils.response import error, success
from backend.utils.secrets import signing_key
from backend.utils.validation import ApiError


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    app.config["SECRET_KEY"] = signing_key(
        app.config.get("SECRET_KEY"), app.config["SECRET_KEY_FILE"]
    )
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    db.init_app(app)
    with app.app_context():
        db.create_all()
        schema_status = ensure_constraints()
        app.extensions["schema_status"] = schema_status
        if schema_status["duplicate_number_groups"] or schema_status["orphan_records"]:
            app.logger.warning(
                "历史数据待核对：重复患者编号 %s 组，未关联患者的病历 %s 条。"
                "已保留原数据，暂缓添加受影响的数据库约束；新增数据仍执行关联和编号校验。",
                schema_status["duplicate_number_groups"], schema_status["orphan_records"],
            )

    @app.before_request
    def authenticate():
        if request.method == "OPTIONS" or not request.path.startswith("/api"):
            return
        if request.endpoint in (None, "spa_fallback"):
            if request.routing_exception:
                raise request.routing_exception
            raise ApiError("接口不存在", 404)
        if request.endpoint in ("health", "user.login"):
            return
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise ApiError("请先登录", 401)
        payload = verify_token(auth[7:])
        user = db.session.get(User, payload["user_id"]) if payload else None
        if (user is None or user.status != 1 or
                not hmac.compare_digest(payload["pwd"], password_version(user.password))):
            raise ApiError("登录已失效，请重新登录", 401)
        g.current_user = user

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(ApiError)
    def api_error(exc):
        return jsonify(error(exc.message, exc.status)), exc.status

    @app.errorhandler(HTTPException)
    def http_error(exc):
        messages = {400: "请求格式错误", 404: "地址不存在", 405: "请求方法不支持",
                    413: "上传内容超过16 MB限制", 415: "请求格式不支持"}
        return jsonify(error(messages.get(exc.code, "请求失败"), exc.code)), exc.code

    @app.errorhandler(SQLAlchemyError)
    def database_error(exc):
        db.session.rollback()
        status = 409 if isinstance(exc, IntegrityError) else 503
        app.logger.warning("Database request failed: %s", type(exc).__name__)
        message = "数据存在冲突，请刷新后重试" if status == 409 else "数据库暂时不可用，请稍后重试"
        return jsonify(error(message, status)), status

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        db.session.rollback()
        app.logger.error("Request failed: %s", type(exc).__name__)
        return jsonify(error("服务暂时不可用，请稍后重试", 500)), 500

    @app.route("/api/health", methods=["GET"])
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify(error("database unavailable", 503)), 503
        return jsonify(success({"database": "ok"}, "ok"))

    frontend_dir = PROJECT_ROOT / "frontend" / "dist"

    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/assets/<path:filename>")
    def assets(filename):
        return send_from_directory(frontend_dir / "assets", filename)

    @app.route("/<path:path>")
    def spa_fallback(path):
        if path == "api" or path.startswith("api/"):
            raise ApiError("接口不存在", 404)
        candidate = (frontend_dir / path).resolve()
        if not candidate.is_relative_to(frontend_dir.resolve()):
            raise ApiError("地址不存在", 404)
        if candidate.is_file():
            return send_from_directory(frontend_dir, path)
        if Path(path).suffix:
            raise ApiError("静态资源不存在", 404)
        return send_from_directory(frontend_dir, "index.html")

    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(patient_bp, url_prefix="/api/patient")
    app.register_blueprint(medical_bp, url_prefix="/api/medical")
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
