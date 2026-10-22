"""只读验证运行中的 Docker 服务；不输出令牌或业务记录。"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def get(path, expected=200, token=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        response = urlopen(Request("http://127.0.0.1:8080" + path, headers=headers), timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read()
        assert response.status == expected, (path, response.status)
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        if path.startswith("/api"):
            assert response.headers.get("Cache-Control") == "no-store"
    return body


def main():
    html = get("/").decode("utf-8")
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert assets
    for asset in assets:
        get(asset)
    for path in ("/home", "/patient", "/medical", "/ai", "/favicon.ico"):
        get(path)
    get("/assets/does-not-exist.js", 404)
    get("/api/health")
    get("/api/does-not-exist", 404)
    get("/api/patient/list", 401)
    # 只读内部诊断令牌只在内存中传递，不写入日志或文件。
    code = """
from backend.app import create_app
from backend.model.user import User
from backend.utils.jwt_util import create_token
app = create_app()
with app.app_context():
    user = User.query.filter_by(status=1).first()
    if user is None:
        raise RuntimeError('No active account available for read-only verification')
    print(create_token(user.id, user.password))
"""
    result = subprocess.run(["docker", "compose", "exec", "-T", "app", "python", "-"],
                            cwd=ROOT, input=code.encode(), capture_output=True, check=True)
    token = result.stdout.decode().strip()
    if "--restart" in sys.argv:
        subprocess.run(["docker", "compose", "restart", "app"], cwd=ROOT,
                       capture_output=True, check=True, timeout=60)
        deadline = time.monotonic() + 60
        while True:
            try:
                get("/api/health")
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
    for path in ("/api/user/me", "/api/user/stats", "/api/patient/list", "/api/medical/list", "/api/rag/status"):
        response = json.loads(get(path, token=token))
        assert response["code"] == 200
    get("/api/user/me", 401, token="invalid-token")
    print(json.dumps({"deployment": "passed", "frontend_assets": len(assets), "authenticated_reads": 5,
                      "pre_restart_token_preserved": "--restart" in sys.argv}))


if __name__ == "__main__":
    main()
