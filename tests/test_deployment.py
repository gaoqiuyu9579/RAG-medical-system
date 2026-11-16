"""部署配置、健康检查和账号初始化回归测试。"""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from backend.app import create_app
from backend.config.database import db


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_KEY": "deployment-test-key-with-at-least-32-characters",
            }
        )
        self.db = db
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_environment_overrides_dotenv_and_handles_password_symbols(self):
        environment = dict(
            os.environ,
            MYSQL_HOST="container-db",
            MYSQL_PORT="3307",
            MYSQL_USER="deployment-test",
            MYSQL_PASSWORD="test@password:/with#symbols",
            MYSQL_DATABASE="deployment_test",
            SECRET_KEY="deployment-test-key",
        )
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json; from backend.config.config import Config; "
                "u=Config.SQLALCHEMY_DATABASE_URI; "
                "print(json.dumps([u.host,u.port,u.username,u.password,Config.SECRET_KEY]))",
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(
            json.loads(result.stdout),
            [
                "container-db",
                3307,
                "deployment-test",
                "test@password:/with#symbols",
                "deployment-test-key",
            ],
        )

    def test_health_checks_database_and_reports_unavailability(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["database"], "ok")
        with patch.object(
            db.session,
            "execute",
            side_effect=OperationalError("SELECT 1", {}, Exception("test database unavailable")),
        ):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)

    def test_bootstrap_login_and_restart_preserve_existing_password(self):
        from deploy.start import bootstrap_admin
        from backend.model.user import User
        from backend.utils.passwords import is_password_hash

        with patch.dict(
            os.environ,
            BOOTSTRAP_ADMIN_USERNAME="test-admin",
            BOOTSTRAP_ADMIN_PASSWORD="first-password",
        ):
            bootstrap_admin(self.app)
        with patch.dict(
            os.environ,
            BOOTSTRAP_ADMIN_USERNAME="test-admin",
            BOOTSTRAP_ADMIN_PASSWORD="replacement-password",
        ):
            bootstrap_admin(self.app)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 1)
            self.assertTrue(is_password_hash(User.query.first().password))
        response = self.client.post(
            "/api/user/login",
            json={
                "username": "test-admin",
                "password": "first-password",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["data"]["token"])
        response = self.client.post(
            "/api/user/login",
            json={
                "username": "test-admin",
                "password": "replacement-password",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_empty_mounted_vector_directory_does_not_call_embedding(self):
        from backend.rag.vector_store import load_vector_store

        with (
            patch("backend.rag.vector_store.os.path.isfile", return_value=False),
            patch("backend.rag.vector_store.get_embedding") as embedding,
        ):
            self.assertIsNone(load_vector_store())
            embedding.assert_not_called()

    def test_demo_seed_is_realistic_idempotent_and_preserves_existing_records(self):
        from backend.model.medical_record import MedicalRecord
        from backend.model.patient import Patient
        from deploy.demo_data import seed_demo_data

        with self.app.app_context():
            self.assertTrue(seed_demo_data())
            self.assertEqual(Patient.query.count(), 12)
            self.assertEqual(MedicalRecord.query.count(), 56)
            patient = Patient.query.filter_by(name="张某某").one()
            self.assertEqual(patient.age, 65)
            self.assertTrue(patient.phone)
            self.assertTrue(patient.address)
            self.assertIn("高血压", patient.medical_history)
            self.assertFalse(seed_demo_data())
            self.assertEqual(MedicalRecord.query.count(), 56)

    def test_demo_seed_does_not_mix_with_existing_patient_or_historical_record(self):
        from backend.model.medical_record import MedicalRecord
        from backend.model.patient import Patient
        from deploy.demo_data import seed_demo_data

        with self.app.app_context():
            db.session.add(Patient(name="已有档案", patient_no="EXISTING"))
            db.session.commit()
            self.assertFalse(seed_demo_data())
            self.assertEqual(Patient.query.count(), 1)
            self.assertEqual(MedicalRecord.query.count(), 0)
            Patient.query.delete()
            db.session.add(MedicalRecord(patient_id=999, diagnosis="历史待核对病历"))
            db.session.commit()
            self.assertFalse(seed_demo_data())
            self.assertEqual(Patient.query.count(), 0)
            self.assertEqual(MedicalRecord.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
