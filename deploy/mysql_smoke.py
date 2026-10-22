"""仅在随机临时 MySQL 库验证部署行为，绝不使用业务库。"""

import json
import os

from backend.app import create_app
from backend.config.database import db
from backend.utils.passwords import hash_password
from backend.model.user import User
from backend.config.schema import ensure_constraints
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


def main():
    database = os.environ.get("MYSQL_DATABASE", "")
    if not database.startswith("medical_test_") or len(database) != len("medical_test_") + 32:
        raise RuntimeError("仅允许使用随机临时测试数据库")
    app = create_app()
    with app.app_context():
        # 在临时库模拟已有旧表，验证补约束迁移与重复启动。
        original = inspect(db.engine)
        with db.engine.begin() as connection:
            for item in original.get_foreign_keys('medical_record'):
                if item['constrained_columns'] == ['patient_id']:
                    connection.execute(text('ALTER TABLE medical_record DROP FOREIGN KEY `' + item['name'] + '`'))
            for item in original.get_unique_constraints('patient'):
                if item['column_names'] == ['patient_no']:
                    connection.execute(text('ALTER TABLE patient DROP INDEX `' + item['name'] + '`'))
        ensure_constraints()
        ensure_constraints()
        inspector = inspect(db.engine)
        assert any(item['column_names'] == ['patient_no'] for item in inspector.get_unique_constraints('patient'))
        assert any(item['constrained_columns'] == ['patient_id'] for item in inspector.get_foreign_keys('medical_record'))
        # 直接 SQL 也必须被数据库约束拦截。
        try:
            db.session.execute(text("INSERT INTO medical_record (patient_id) VALUES (9223372036854775807)"))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        else:
            raise AssertionError('缺少患者外键约束')
        db.session.add(User(username="smoke-admin", password=hash_password("SmokeTestPassword123"), role="admin", status=1))
        db.session.commit()
    client = app.test_client()
    response = client.post("/api/user/login", json={"username": "smoke-admin", "password": "SmokeTestPassword123"})
    assert response.status_code == 200
    headers = {"Authorization": "Bearer " + response.json["data"]["token"]}
    patient = client.post("/api/patient/add", json={"name": "合成测试", "age": "", "patient_no": "MYSQL-SMOKE-01"}, headers=headers)
    assert patient.status_code == 200, patient.json
    identifier = patient.json["data"]["id"]
    assert isinstance(identifier, int) and identifier > 0
    duplicate = client.post("/api/patient/add", json={"name": "合成测试", "patient_no": "MYSQL-SMOKE-01"}, headers=headers)
    assert duplicate.status_code == 409
    record = client.post("/api/medical/add", json={"patient_id": identifier, "diagnosis": "合成测试"}, headers=headers)
    assert record.status_code == 200, record.json
    assert client.delete(f"/api/patient/delete/{identifier}", headers=headers).status_code == 409
    assert client.delete(f"/api/medical/delete/{record.json['data']['id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/patient/delete/{identifier}", headers=headers).status_code == 200
    assert client.get("/api/user/stats", headers=headers).json["data"]["patientCount"] == 0
    assert client.post("/api/user/password", json={"old_password": "SmokeTestPassword123", "new_password": "ChangedSmokePassword456"}, headers=headers).status_code == 200
    assert client.get("/api/user/me", headers=headers).status_code == 401
    print(json.dumps({"mysql_smoke": "passed", "checks": 16, "database": database}))


if __name__ == "__main__":
    main()
