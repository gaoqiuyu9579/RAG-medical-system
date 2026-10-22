"""JWT 签发、校验和密码变更后的会话失效。"""

import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app


def password_version(password_hash):
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def create_token(user_id, password_hash):
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        "pwd": password_version(password_hash),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def verify_token(token):
    try:
        payload = jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"],
            options={"require": ["exp", "user_id", "pwd"]},
        )
        user_id = payload["user_id"]
        if isinstance(user_id, bool) or not isinstance(user_id, int) or not 0 < user_id <= 9223372036854775807:
            return None
        if not isinstance(payload["pwd"], str):
            return None
        return payload
    except jwt.InvalidTokenError:
        return None
