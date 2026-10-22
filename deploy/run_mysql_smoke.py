"""从主机创建、检查并清理专用测试库，不改动已有数据库。"""

import re
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compose(*args, **kwargs):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True, **kwargs)


def sql(statement):
    compose(
        "exec",
        "-T",
        "mysql",
        "sh",
        "-c",
        'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD"',
        input=statement.encode(),
        capture_output=True,
    )


def main():
    name = "medical_test_" + uuid.uuid4().hex
    user = compose(
        "exec",
        "-T",
        "app",
        "python",
        "-c",
        "import os; print(os.environ['MYSQL_USER'])",
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not re.fullmatch(r"[A-Za-z0-9_]+", user):
        raise RuntimeError("测试脚本只支持字母数字下划线数据库用户名")
    created = False
    try:
        sql(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4;")
        created = True
        sql(f"GRANT ALL PRIVILEGES ON `{name}`.* TO '{user}'@'%';")
        result = compose(
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "-e",
            "MYSQL_DATABASE=" + name,
            "app",
            "python",
            "-",
            input=(ROOT / "deploy/mysql_smoke.py").read_bytes(),
            capture_output=True,
        )
        print(result.stdout.decode("utf-8"))
    finally:
        if created:
            if not re.fullmatch(r"medical_test_[0-9a-f]{32}", name):
                raise RuntimeError("拒绝清理非测试数据库")
            sql(f"DROP DATABASE `{name}`;")
            # 清理测试库授权记录，避免遗留无效权限。
            sql(f"REVOKE ALL PRIVILEGES ON `{name}`.* FROM '{user}'@'%';")
            print("临时测试库及授权已清理。")


if __name__ == "__main__":
    main()
