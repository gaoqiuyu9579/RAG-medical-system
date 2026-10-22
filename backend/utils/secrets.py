"""为未配置独立密钥的部署生成可跨重启保存的随机签名密钥。"""

import os
import secrets
from pathlib import Path


PLACEHOLDERS = {
    "smart-medical-secret",
    "smart-medical-docker-local-secret",
    "replace-with-your-own-random-secret",
}


def signing_key(configured, filename):
    if configured and configured not in PLACEHOLDERS:
        return configured
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        key = path.read_text(encoding="utf-8").strip()
        if len(key) < 32:
            raise RuntimeError("持久化签名密钥无效，请检查 SECRET_KEY_FILE")
        return key
    key = secrets.token_urlsafe(48)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(key)
    return key
