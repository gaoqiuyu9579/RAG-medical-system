"""只读验证运行中的 Docker 服务；不输出令牌或业务记录。"""

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8080"


def get(path, expected=200, token=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        response = urlopen(Request(BASE_URL + path, headers=headers), timeout=10)
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
    global BASE_URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=BASE_URL, help="应用地址，例如 http://127.0.0.1:8081")
    parser.add_argument("--project", help="Compose 项目名；演示模式使用 smart-medical-demo")
    parser.add_argument("--restart", action="store_true", help="重启应用后核对登录凭证仍有效")
    args = parser.parse_args()
    BASE_URL = args.url.rstrip("/")
    compose = ["docker", "compose"]
    if args.project:
        compose += ["--project-name", args.project]
    html = get("/").decode("utf-8")
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert assets
    for asset in assets:
        get(asset)
    for path in ("/home", "/patient", "/medical", "/ai", "/statistics", "/favicon.ico"):
        get(path)
    get("/assets/does-not-exist.js", 404)
    get("/api/health")
    get("/api/does-not-exist", 404)
    get("/api/patient/list", 401)
    # 只读内部诊断令牌只在内存中传递，不写入日志或文件。
    code = """
import hashlib
import json
from pathlib import Path
from backend.app import create_app
from backend.model.user import User
from backend.utils.jwt_util import create_token
app = create_app()
with app.app_context():
    user = User.query.filter_by(status=1).first()
    if user is None:
        raise RuntimeError('No active account available for read-only verification')
    sources = {
        path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in ('backend', 'deploy')
        for path in Path(directory).rglob('*.py')
    }
    print(json.dumps({'token': create_token(user.id, user.password), 'sources': sources}))
"""
    result = subprocess.run(
        [*compose, "exec", "-T", "app", "python", "-"],
        cwd=ROOT,
        input=code.encode(),
        capture_output=True,
        check=True,
    )
    internal = json.loads(result.stdout)
    token = internal["token"]
    source_count = 0
    for directory in ("backend", "deploy"):
        for path in (ROOT / directory).rglob("*.py"):
            if any(
                part.startswith(".") or part == "__pycache__"
                for part in path.relative_to(ROOT).parts
            ):
                continue
            relative = path.relative_to(ROOT).as_posix()
            assert (
                internal["sources"].get(relative) == hashlib.sha256(path.read_bytes()).hexdigest()
            ), ("Container source is outdated", relative)
            source_count += 1
    if args.restart:
        subprocess.run(
            [*compose, "restart", "app"],
            cwd=ROOT,
            capture_output=True,
            check=True,
            timeout=60,
        )
        deadline = time.monotonic() + 60
        while True:
            try:
                get("/api/health")
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
    for path in (
        "/api/user/me",
        "/api/user/stats",
        "/api/patient/list",
        "/api/medical/list",
        "/api/rag/status",
    ):
        response = json.loads(get(path, token=token))
        assert response["code"] == 200
    for days in (7, 30, 90):
        data = json.loads(get(f"/api/user/analytics?days={days}", token=token))["data"]
        assert len(data["trend"]) == days
        assert sum(item["value"] for item in data["ageDistribution"]) == data["patientCount"]
    get("/api/user/me", 401, token="invalid-token")
    print(
        json.dumps(
            {
                "deployment": "passed",
                "frontend_assets": len(assets),
                "authenticated_reads": 8,
                "synchronized_python_files": source_count,
                "pre_restart_token_preserved": args.restart,
            }
        )
    )


if __name__ == "__main__":
    main()
