"""显式启用后，仅在随机 MySQL 测试库验证历史数据启动兼容。"""

import os
import re
import unittest
import uuid

from sqlalchemy import create_engine, inspect, text

from backend.app import create_app
from backend.config.config import Config
from backend.config.database import db
from backend.config.schema import ensure_constraints
from backend.service.medical_service import MedicalService
from backend.utils.validation import ApiError


@unittest.skipUnless(os.getenv("MYSQL_SCHEMA_TESTS") == "1", "仅显式启用时使用随机 MySQL 测试库")
class LegacySchemaTests(unittest.TestCase):
    def setUp(self):
        self.name = "medical_schema_test_" + uuid.uuid4().hex
        self.root_engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        with self.root_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE `{self.name}` CHARACTER SET utf8mb4"))
        self.addCleanup(self.cleanup_database)
        self.config = {
            "TESTING": True,
            "SECRET_KEY": "legacy-test-secret-with-at-least-32-characters",
            "SQLALCHEMY_DATABASE_URI": Config.SQLALCHEMY_DATABASE_URI.set(database=self.name),
        }
        self.app = create_app(self.config)
        with self.app.app_context():
            inspector = inspect(db.engine)
            with db.engine.begin() as connection:
                for item in inspector.get_foreign_keys("medical_record"):
                    connection.execute(
                        text("ALTER TABLE medical_record DROP FOREIGN KEY `" + item["name"] + "`")
                    )
                for item in inspector.get_unique_constraints("patient"):
                    if item["column_names"] == ["patient_no"]:
                        connection.execute(
                            text("ALTER TABLE patient DROP INDEX `" + item["name"] + "`")
                        )

    def cleanup_database(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        if not re.fullmatch(r"medical_schema_test_[0-9a-f]{32}", self.name):
            raise RuntimeError("拒绝清理非测试数据库")
        with self.root_engine.connect() as connection:
            connection.execute(text(f"DROP DATABASE `{self.name}`"))
        self.root_engine.dispose()

    def execute(self, *statements):
        with self.app.app_context(), db.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def inspect_status(self):
        with self.app.app_context():
            return ensure_constraints()

    def test_orphan_records_do_not_prevent_startup_or_get_reassigned(self):
        self.execute(
            "INSERT INTO patient (id,patient_no,name) VALUES (4,'P4','合成患者')",
            "INSERT INTO medical_record (id,patient_id,diagnosis) VALUES (1,1,'合成记录'),(2,2,'合成记录'),(7,1,'合成记录')",
        )
        app = create_app(self.config)
        status = app.extensions["schema_status"]
        self.assertEqual(status["orphan_records"], 3)
        self.assertTrue(status["patient_number_unique"])
        self.assertFalse(status["medical_patient_foreign_key"])
        self.assertEqual(app.test_client().get("/api/health").status_code, 200)
        with app.app_context():
            rows = list(
                db.session.execute(text("SELECT id,patient_id FROM medical_record ORDER BY id"))
            )
            self.assertEqual([tuple(row) for row in rows], [(1, 1), (2, 2), (7, 1)])
            self.assertEqual(db.session.execute(text("SELECT COUNT(*) FROM patient")).scalar(), 1)
            with self.assertRaises(ApiError):
                MedicalService.add_record({"patient_id": 999, "diagnosis": "拒绝新增孤立记录"})

    def test_duplicate_numbers_only_defer_unique_constraint(self):
        self.execute(
            "INSERT INTO patient (id,patient_no,name) VALUES (1,'DUP','测试一'),(2,'DUP','测试二')"
        )
        app = create_app(self.config)
        status = app.extensions["schema_status"]
        self.assertEqual(status["duplicate_number_groups"], 1)
        self.assertFalse(status["patient_number_unique"])
        self.assertTrue(status["medical_patient_foreign_key"])
        self.assertEqual(app.test_client().get("/api/health").status_code, 200)
        with app.app_context():
            self.assertEqual(
                db.session.execute(
                    text("SELECT COUNT(*) FROM patient WHERE patient_no='DUP'")
                ).scalar(),
                2,
            )

    def test_constraints_are_applied_after_conflicts_are_resolved(self):
        self.execute(
            "INSERT INTO patient (id,patient_no) VALUES (1,'DUP'),(2,'DUP')",
            "INSERT INTO medical_record (id,patient_id) VALUES (1,999)",
        )
        initial = self.inspect_status()
        self.assertFalse(initial["patient_number_unique"])
        self.assertFalse(initial["medical_patient_foreign_key"])
        self.execute(
            "UPDATE patient SET patient_no='P2' WHERE id=2",
            "UPDATE medical_record SET patient_id=1 WHERE id=1",
        )
        repaired = self.inspect_status()
        self.assertTrue(repaired["patient_number_unique"])
        self.assertTrue(repaired["medical_patient_foreign_key"])
        self.assertEqual(repaired, self.inspect_status())

    def test_clean_legacy_tables_receive_both_constraints(self):
        status = self.inspect_status()
        self.assertEqual(status["orphan_records"], 0)
        self.assertEqual(status["duplicate_number_groups"], 0)
        self.assertTrue(status["patient_number_unique"])
        self.assertTrue(status["medical_patient_foreign_key"])


if __name__ == "__main__":
    unittest.main()
