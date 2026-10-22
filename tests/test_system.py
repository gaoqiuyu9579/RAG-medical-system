"""独立数据库中的接口、认证、数据完整性及输入边界回归测试。"""

import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
from sqlalchemy.exc import OperationalError

from backend.app import create_app
from backend.config.database import db
from backend.model.user import User
from backend.utils.jwt_util import password_version
from backend.utils.passwords import hash_password, is_password_hash


class SystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_hash = hash_password("TestPassword123")

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_KEY": "system-tests-signing-key-32-characters-minimum",
                "DASHSCOPE_API_KEY": "",
                "DEEPSEEK_API_KEY": "",
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.session.add(User(username="admin", password=self.admin_hash, role="admin", status=1))
            db.session.commit()
        response = self.client.post(
            "/api/user/login",
            json={
                "username": "admin",
                "password": "TestPassword123",
            },
        )
        self.token = response.json["data"]["token"]
        self.headers = {"Authorization": "Bearer " + self.token}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def post(self, path, data):
        return self.client.post(path, json=data, headers=self.headers)

    def patient(self, **fields):
        response = self.post("/api/patient/add", {"name": "测试患者", **fields})
        self.assertEqual(response.status_code, 200, response.json)
        return response.json["data"]

    def test_all_business_routes_require_authentication(self):
        routes = [
            ("GET", "/api/user/list"),
            ("GET", "/api/user/me"),
            ("GET", "/api/user/stats"),
            ("GET", "/api/patient/list"),
            ("POST", "/api/patient/add"),
            ("DELETE", "/api/patient/delete/1"),
            ("GET", "/api/medical/list"),
            ("POST", "/api/medical/add"),
            ("DELETE", "/api/medical/delete/1"),
            ("POST", "/api/user/password"),
            ("GET", "/api/rag/status"),
            ("POST", "/api/rag/upload"),
            ("POST", "/api/rag/upload-file"),
            ("POST", "/api/rag/chat"),
        ]
        for method, path in routes:
            with self.subTest(path=path):
                response = self.client.open(path, method=method)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json["code"], 401)

    def test_expired_forged_and_malformed_tokens_are_rejected(self):
        expired = jwt.encode(
            {
                "user_id": 1,
                "pwd": password_version(self.admin_hash),
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            self.app.config["SECRET_KEY"],
            algorithm="HS256",
        )
        for token in ("garbage", expired, self.token[:-4] + "abcd"):
            with self.subTest(token=token[:8]):
                response = self.client.get(
                    "/api/patient/list", headers={"Authorization": "Bearer " + token}
                )
                self.assertEqual(response.status_code, 401)

    def test_legacy_password_migrates_without_password_reset(self):
        with self.app.app_context():
            db.session.add(User(username="legacy", password="legacy-pass", role="doctor", status=1))
            db.session.commit()
        response = self.client.post(
            "/api/user/login", json={"username": "legacy", "password": "legacy-pass"}
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertTrue(
                is_password_hash(User.query.filter_by(username="legacy").first().password)
            )
        self.assertNotIn("password", response.json["data"]["user"])

    def test_disabled_accounts_cannot_login_or_use_existing_tokens(self):
        with self.app.app_context():
            User.query.first().status = 0
            db.session.commit()
        self.assertEqual(self.client.get("/api/user/me", headers=self.headers).status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/user/login",
                json={
                    "username": "admin",
                    "password": "TestPassword123",
                },
            ).status_code,
            401,
        )

    def test_user_list_requires_admin_role(self):
        with self.app.app_context():
            User.query.first().role = "doctor"
            db.session.commit()
        self.assertEqual(self.client.get("/api/user/list", headers=self.headers).status_code, 403)
        self.assertEqual(
            self.client.get("/api/patient/list", headers=self.headers).status_code, 200
        )

    def test_password_change_invalidates_old_tokens_and_accepts_new_password(self):
        response = self.post(
            "/api/user/password",
            {
                "old_password": "TestPassword123",
                "new_password": "ChangedPassword456",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/user/me", headers=self.headers).status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/user/login",
                json={
                    "username": "admin",
                    "password": "TestPassword123",
                },
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/api/user/login",
                json={
                    "username": "admin",
                    "password": "ChangedPassword456",
                },
            ).status_code,
            200,
        )

    def test_password_change_rejects_wrong_short_and_identical_passwords(self):
        for old, new in (
            ("wrong", "ChangedPassword456"),
            ("TestPassword123", "short"),
            ("TestPassword123", "TestPassword123"),
        ):
            with self.subTest(new=new):
                self.assertEqual(
                    self.post(
                        "/api/user/password",
                        {
                            "old_password": old,
                            "new_password": new,
                        },
                    ).status_code,
                    400,
                )

    def test_invalid_json_and_missing_login_fields_return_400(self):
        for value in (
            None,
            [],
            "text",
            {},
            {"username": "admin"},
            {"username": True, "password": "abc"},
            {"username": "admin", "password": []},
        ):
            with self.subTest(value=value):
                response = self.client.post("/api/user/login", json=value)
                self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/user/login", data="{", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_patient_optional_age_and_generated_number(self):
        first = self.patient(age="", name="  测试患者  ")
        second = self.patient()
        self.assertIsNone(first["age"])
        self.assertEqual(first["name"], "测试患者")
        self.assertTrue(first["patient_no"].startswith("P"))
        self.assertNotEqual(first["patient_no"], second["patient_no"])

    def test_patient_validation_and_duplicate_numbers(self):
        for data in (
            {"name": " "},
            {"name": 10},
            {"name": "a" * 51},
            {"name": "测试", "age": -1},
            {"name": "测试", "age": True},
            {"name": "测试", "age": "1.5"},
            {"name": "测试", "age": 151},
            {"name": "测试", "gender": "invalid"},
            {"name": "测试", "phone": "1" * 21},
        ):
            with self.subTest(data=data):
                self.assertEqual(self.post("/api/patient/add", data).status_code, 400)
        self.patient(patient_no="TEST-UNIQUE")
        self.assertEqual(
            self.post(
                "/api/patient/add", {"name": "测试", "patient_no": "TEST-UNIQUE"}
            ).status_code,
            409,
        )

    def test_medical_record_requires_an_existing_patient(self):
        self.assertEqual(self.post("/api/medical/add", {"patient_id": 999}).status_code, 404)
        for value in (None, "", 0, -1, True, "1.2", "9" * 100):
            with self.subTest(value=value):
                self.assertEqual(
                    self.post("/api/medical/add", {"patient_id": value}).status_code, 400
                )

    def test_patient_with_records_is_protected_then_can_be_deleted(self):
        patient = self.patient()
        record = self.post("/api/medical/add", {"patient_id": patient["id"], "diagnosis": "测试"})
        self.assertEqual(record.status_code, 200)
        self.assertEqual(
            self.client.delete(
                f"/api/patient/delete/{patient['id']}", headers=self.headers
            ).status_code,
            409,
        )
        record_id = record.json["data"]["id"]
        self.assertEqual(
            self.client.delete(
                f"/api/medical/delete/{record_id}", headers=self.headers
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/patient/delete/{patient['id']}", headers=self.headers
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/patient/delete/{patient['id']}", headers=self.headers
            ).status_code,
            404,
        )

    def test_missing_and_oversized_deletion_ids_are_safe(self):
        for kind in ("patient", "medical"):
            for identifier in (999, "9" * 100):
                self.assertEqual(
                    self.client.delete(
                        f"/api/{kind}/delete/{identifier}", headers=self.headers
                    ).status_code,
                    404,
                )

    def test_database_failure_rolls_back_and_next_request_succeeds(self):
        with patch.object(
            db.session, "commit", side_effect=OperationalError("INSERT", {}, Exception("test"))
        ):
            response = self.post("/api/patient/add", {"name": "不应保存"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            self.client.get("/api/patient/list", headers=self.headers).json["data"], []
        )

    def test_stats_are_derived_from_database(self):
        patient = self.patient()
        self.post("/api/medical/add", {"patient_id": patient["id"]})
        result = self.client.get("/api/user/stats", headers=self.headers).json["data"]
        self.assertEqual(result, {"patientCount": 1, "recordCount": 1, "todayVisit": 1})

    def test_unknown_api_and_wrong_method_return_json_errors(self):
        response = self.client.get("/api/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.is_json)
        response = self.client.post("/api/health")
        self.assertEqual(response.status_code, 405)
        self.assertTrue(response.is_json)
        self.assertEqual(self.client.get("/assets/missing.js").status_code, 404)
        self.assertEqual(self.client.get("/missing.css").status_code, 404)

    def test_security_headers_and_restricted_cors(self):
        response = self.client.get("/api/health", headers={"Origin": "https://untrusted.example"})
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        response = self.client.options(
            "/api/patient/list",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_rag_whitespace_and_type_validation(self):
        for path, key in (("/api/rag/upload", "text"), ("/api/rag/chat", "question")):
            for value in (" ", None, [], 123):
                self.assertEqual(self.post(path, {key: value}).status_code, 400)
        self.assertEqual(self.post("/api/rag/chat", {"question": "a" * 2001}).status_code, 400)

    def test_upload_missing_wrong_extension_encoding_and_empty_file(self):
        self.assertEqual(
            self.client.post("/api/rag/upload-file", headers=self.headers).status_code, 400
        )
        for filename, content in (
            ("test.exe", b"binary"),
            ("test.txt", b"\xff\xfe"),
            ("test.txt", b"  "),
            ("test.pdf", b"not a pdf"),
        ):
            with self.subTest(filename=filename, content=content):
                response = self.client.post(
                    "/api/rag/upload-file",
                    headers=self.headers,
                    data={"file": (io.BytesIO(content), filename)},
                )
                self.assertEqual(response.status_code, 400)

    def test_utf8_bom_upload_preserves_safe_source_name(self):
        with patch(
            "backend.controller.rag_controller.RagService.upload_text",
            return_value={"added": 1, "total": 1},
        ) as upload:
            response = self.client.post(
                "/api/rag/upload-file",
                headers=self.headers,
                data={
                    "file": (io.BytesIO("\ufeff测试资料".encode("utf-8")), "../知识.txt"),
                },
            )
        self.assertEqual(response.status_code, 200)
        upload.assert_called_once_with("测试资料", "知识.txt")

    def test_oversized_http_payload_returns_413(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 1024
        response = self.post("/api/rag/upload", {"text": "x" * 2048})
        self.assertEqual(response.status_code, 413)

    def test_rag_errors_do_not_leak_upstream_secrets(self):
        with patch(
            "backend.controller.rag_controller.RagService.chat",
            side_effect=RuntimeError("sk-SECRET-EXAMPLE"),
        ):
            response = self.post("/api/rag/chat", {"question": "测试"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SECRET", response.get_data(as_text=True))

    def test_missing_embedding_key_returns_clear_service_error(self):
        response = self.post("/api/rag/upload", {"text": "测试资料"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("DASHSCOPE_API_KEY", response.json["msg"])

    def test_empty_knowledge_base_never_calls_models(self):
        with (
            patch("backend.rag.qa_chain.load_vector_store", return_value=None),
            patch("backend.rag.qa_chain.get_llm") as llm,
        ):
            response = self.post("/api/rag/chat", {"question": "测试"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("知识库为空", response.json["data"]["answer"])
        llm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
