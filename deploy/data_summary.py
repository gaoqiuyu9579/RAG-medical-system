"""Docker 内只读数据核对，不输出账号密码或患者资料。"""

import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pymysql


def main():
    connection = pymysql.connect(host=os.environ["MYSQL_HOST"], port=int(os.getenv("MYSQL_PORT", "3306")),
                                 user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWORD"],
                                 database=os.environ["MYSQL_DATABASE"])
    result = {}
    with connection:
        with connection.cursor() as cursor:
            for table in ("sys_user", "patient", "medical_record"):
                cursor.execute("SELECT COUNT(*) FROM " + table)
                result[table] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM medical_record m LEFT JOIN patient p ON p.id=m.patient_id WHERE p.id IS NULL")
            result["orphan_records"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM (SELECT patient_no FROM patient WHERE patient_no IS NOT NULL AND patient_no<>'' GROUP BY patient_no HAVING COUNT(*)>1) t")
            result["duplicate_patient_numbers"] = cursor.fetchone()[0]
    filename = Path("/app/backend/chroma_db/chroma.sqlite3")
    result["knowledge_chunks"] = 0
    if filename.is_file():
        with sqlite3.connect(filename.as_uri() + "?mode=ro", uri=True) as vector_db:
            result["knowledge_chunks"] = vector_db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    key = Path("/app/instance/jwt.secret")
    if key.is_file():
        result["signing_key_fingerprint"] = hashlib.sha256(key.read_bytes()).hexdigest()[:16]
    print(json.dumps(result))


if __name__ == "__main__":
    main()
