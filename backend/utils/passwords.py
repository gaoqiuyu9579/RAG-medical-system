"""密码哈希以及旧版明文账号的兼容校验。"""

import hmac

from werkzeug.security import check_password_hash, generate_password_hash


def is_password_hash(value):
    return isinstance(value, str) and value.startswith(("scrypt:", "pbkdf2:"))


def hash_password(password):
    return generate_password_hash(password)


def verify_password(stored, password):
    if not isinstance(stored, str) or not isinstance(password, str):
        return False
    if is_password_hash(stored):
        try:
            return check_password_hash(stored, password)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(stored.encode("utf-8"), password.encode("utf-8"))
