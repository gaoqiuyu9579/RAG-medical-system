"""为已有 MySQL 表补充可应用的约束；冲突的历史数据保留待核对。"""

from sqlalchemy import inspect, text

from backend.config.database import db


def ensure_constraints():
    if db.engine.dialect.name != "mysql":
        return {"duplicate_number_groups": 0, "orphan_records": 0}
    # MySQL DDL 自动提交；独立连接和命名锁避免多实例重复迁移。
    with db.engine.connect() as connection:
        locked = connection.execute(text("SELECT GET_LOCK('medical_schema_v2', 30)")).scalar()
        if locked != 1:
            raise RuntimeError("无法获得数据库升级锁")
        try:
            duplicate = connection.execute(
                text(
                    "SELECT COUNT(*) FROM (SELECT patient_no FROM patient WHERE patient_no IS NOT NULL "
                    "GROUP BY patient_no HAVING COUNT(*) > 1) duplicate_numbers"
                )
            ).scalar()
            orphan = connection.execute(
                text(
                    "SELECT COUNT(*) FROM medical_record m LEFT JOIN patient p ON p.id=m.patient_id "
                    "WHERE p.id IS NULL"
                )
            ).scalar()
            inspector = inspect(connection)
            unique = inspector.get_unique_constraints("patient")
            has_unique = any(item["column_names"] == ["patient_no"] for item in unique)
            if not has_unique and not duplicate:
                connection.execute(
                    text("ALTER TABLE patient ADD CONSTRAINT uq_patient_no UNIQUE (patient_no)")
                )
                has_unique = True
            foreign_keys = inspector.get_foreign_keys("medical_record")
            has_foreign_key = any(
                item["constrained_columns"] == ["patient_id"]
                and item["referred_table"] == "patient"
                and item["referred_columns"] == ["id"]
                for item in foreign_keys
            )
            if not has_foreign_key and not orphan:
                connection.execute(
                    text(
                        "ALTER TABLE medical_record ADD CONSTRAINT fk_medical_patient "
                        "FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE RESTRICT"
                    )
                )
                has_foreign_key = True
            return {
                "duplicate_number_groups": duplicate,
                "orphan_records": orphan,
                "patient_number_unique": has_unique,
                "medical_patient_foreign_key": has_foreign_key,
            }
        finally:
            connection.execute(text("SELECT RELEASE_LOCK('medical_schema_v2')"))
