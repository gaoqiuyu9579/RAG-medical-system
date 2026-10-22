"""备份当前 Docker 部署，不输出密码或业务记录。"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def docker(*args, **kwargs):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True, **kwargs)


def main():
    target = ROOT / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    target.mkdir(parents=True, exist_ok=False)
    container = docker("ps", "-q", "app", capture_output=True, text=True).stdout.strip()
    if not container:
        raise RuntimeError("应用容器未运行，未开始备份")
    paused = False
    try:
        # 暂停应用写入，使关系数据和知识库来自同一维护窗口。
        docker("pause", "app", capture_output=True)
        paused = True
        with (target / "mysql.sql").open("wb") as stream:
            docker("exec", "-T", "mysql", "sh", "-c",
                   'exec mysqldump --single-transaction --no-tablespaces --set-gtid-purged=OFF -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"',
                   stdout=stream, stderr=subprocess.PIPE)
        subprocess.run(["docker", "cp", container + ":/app/backend/chroma_db", str(target / "chroma_db")],
                       check=True, capture_output=True)
        # 旧镜像没有 instance 目录；新镜像需一并保存签名密钥。
        instance = subprocess.run(["docker", "cp", container + ":/app/instance", str(target / "instance")],
                                  capture_output=True)
        metadata = {"created": datetime.now().isoformat(), "instance_included": instance.returncode == 0,
                    "mysql_bytes": (target / "mysql.sql").stat().st_size,
                    "chroma_files": sum(1 for path in (target / "chroma_db").rglob("*") if path.is_file())}
        if not metadata["mysql_bytes"]:
            raise RuntimeError("数据库备份为空")
        (target / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps({"backup": str(target), **metadata}, ensure_ascii=False))
    finally:
        if paused:
            docker("unpause", "app", capture_output=True)


if __name__ == "__main__":
    main()
