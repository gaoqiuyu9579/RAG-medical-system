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
            ("GET", "/api/patient/search"),
            ("GET", "/api/patient/detail/1"),
            ("POST", "/api/patient/add"),
            ("PUT", "/api/patient/update/1"),
            ("POST", "/api/patient/restore"),
            ("DELETE", "/api/patient/delete/1"),
            ("GET", "/api/medical/list"),
            ("POST", "/api/medical/add"),
            ("PUT", "/api/medical/update/1"),
            ("POST", "/api/medical/restore"),
            ("DELETE", "/api/medical/delete/1"),
            ("POST", "/api/user/password"),
            ("GET", "/api/rag/status"),
            ("POST", "/api/rag/upload"),
            ("POST", "/api/rag/upload-file"),
            ("POST", "/api/rag/chat"),
            ("POST", "/api/rag/chat-stream"),
            ("POST", "/api/rag/upload-stream"),
            ("GET", "/api/user/analytics"),
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

    def search_patients(self, **params):
        response = self.client.get("/api/patient/search", query_string=params, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        return response.json["data"]

    def test_patient_search_pagination_empty_pages_and_legacy_list(self):
        self.assertEqual(
            self.search_patients(),
            {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
                "pages": 0,
            },
        )
        patients = [self.patient(name="同名患者", medical_history="仅详情可见") for _ in range(3)]
        first = self.search_patients(page_size=2)
        second = self.search_patients(page=2, page_size=2)
        self.assertEqual(
            [row["id"] for row in first["items"]], [patients[2]["id"], patients[1]["id"]]
        )
        self.assertEqual([row["id"] for row in second["items"]], [patients[0]["id"]])
        self.assertEqual((first["total"], first["pages"], first["page_size"]), (3, 2, 2))
        self.assertEqual(second["page"], 2)
        self.assertEqual(
            set(first["items"][0]),
            {
                "id",
                "patient_no",
                "name",
                "gender",
                "age",
                "phone",
                "create_time",
            },
        )
        self.assertIsNone(first["items"][0]["age"])
        self.assertEqual(first["items"][0]["create_time"], patients[2]["create_time"])
        for page in (3, 2147483647):
            result = self.search_patients(page=page, page_size=2)
            self.assertEqual(result["items"], [])
            self.assertEqual(result["total"], 3)
        legacy = self.client.get("/api/patient/list", headers=self.headers).json["data"]
        self.assertEqual(legacy, patients[::-1])
        self.assertEqual(self.search_patients(page=" ", page_size="")["page_size"], 20)
        self.assertEqual(self.search_patients(page_size=100)["page_size"], 100)

    def test_patient_search_names_and_exact_identifiers(self):
        first = self.patient(name="张三", patient_no="MRN-100", phone="13800000001")
        second = self.patient(name="张三丰", patient_no="MRN-1000", phone="138000000010")
        self.patient(name="李四", patient_no="MRN-200", phone="13900000001")
        cases = [
            ({"keyword": " 张三 "}, [second["id"], first["id"]]),
            ({"name": "张三"}, [second["id"], first["id"]]),
            ({"keyword": "MRN-100"}, [first["id"]]),
            ({"patient_no": " MRN-100 "}, [first["id"]]),
            ({"keyword": "13800000001"}, [first["id"]]),
            ({"phone": "13800000001"}, [first["id"]]),
            ({"patient_no": "MRN-10"}, []),
            ({"phone": "1380000000"}, []),
            ({"keyword": "MRN-100", "name": "李"}, []),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                self.assertEqual(
                    [row["id"] for row in self.search_patients(**params)["items"]], expected
                )

    def test_patient_search_combines_filters_and_handles_unknown_age(self):
        newborn = self.patient(name="张新生", gender="男", age=0)
        first = self.patient(name="张患者", gender="男", age=65, phone="13800000001")
        second = self.patient(name="张患者", gender="女", age=70)
        self.patient(name="张患者", gender="男", age=None)
        oldest = self.patient(name="边界患者", gender="未知", age=150)
        cases = [
            ({"name": "张", "gender": "男", "age_min": 60, "age_max": 70}, [first["id"]]),
            ({"age_min": 0, "age_max": 0}, [newborn["id"]]),
            ({"age_max": 65}, [first["id"], newborn["id"]]),
            ({"age_min": 70}, [oldest["id"], second["id"]]),
            ({"gender": "未知", "age_min": 150, "age_max": 150}, [oldest["id"]]),
            (
                {"patient_no": first["patient_no"], "phone": first["phone"], "gender": "男"},
                [first["id"]],
            ),
            ({"patient_no": first["patient_no"], "gender": "女"}, []),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                self.assertEqual(
                    [row["id"] for row in self.search_patients(**params)["items"]], expected
                )

    def test_patient_search_treats_wildcards_and_sql_as_literal_text(self):
        self.patient(name="普通患者")
        for marker in ("%", "_", "/", "\\", "' OR 1=1 --"):
            patient = self.patient(name=f"代号{marker}患者")
            for field in ("keyword", "name"):
                with self.subTest(marker=marker, field=field):
                    result = self.search_patients(**{field: marker})
                    self.assertEqual([row["id"] for row in result["items"]], [patient["id"]])

    def test_patient_search_rejects_invalid_and_ambiguous_parameters(self):
        cases = [
            {"page": 0},
            {"page": -1},
            {"page": "1.5"},
            {"page": "true"},
            {"page": "2147483648"},
            {"page": "9" * 5000},
            {"page_size": 0},
            {"page_size": 101},
            {"page_size": "NaN"},
            {"age_min": -1},
            {"age_max": 151},
            {"age_min": "1.5"},
            {"age_min": 80, "age_max": 60},
            {"age_max": "9" * 5000},
            {"gender": "invalid"},
            {"keyword": "字" * 51},
            {"name": "字" * 51},
            {"patient_no": "P" * 51},
            {"phone": "1" * 21},
            {"sort": "id desc"},
            {"patient_n0": "TYPO"},
            {"page[]": "1"},
            [("page", "1"), ("page", "2")],
            [("keyword", "张"), ("keyword", "")],
        ]
        for params in cases:
            with self.subTest(params=str(params)[:100]):
                response = self.client.get(
                    "/api/patient/search", query_string=params, headers=self.headers
                )
                self.assertEqual(response.status_code, 400, response.json)
                self.assertEqual(response.json["code"], 400)
                self.assertIsNone(response.json["data"])

    def test_patient_detail_returns_archive_and_missing_ids_return_404(self):
        patient = self.patient(name="张同名", address="合成地址", medical_history="合成病史")
        self.patient(name="张同名")
        response = self.client.get(f"/api/patient/detail/{patient['id']}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"], patient)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        for patient_id in (0, 999, 9223372036854775808, "9" * 100):
            with self.subTest(patient_id=patient_id):
                response = self.client.get(
                    f"/api/patient/detail/{patient_id}", headers=self.headers
                )
                self.assertEqual(response.status_code, 404, response.json)
                self.assertIsNone(response.json["data"])

    def test_doctors_can_use_patient_search_and_detail_with_existing_authentication(self):
        patient = self.patient()
        with self.app.app_context():
            User.query.first().role = "doctor"
            db.session.commit()
        self.assertEqual(self.search_patients()["total"], 1)
        self.assertEqual(
            self.client.get(
                f"/api/patient/detail/{patient['id']}", headers=self.headers
            ).status_code,
            200,
        )
        for method, path in (("POST", "/api/patient/search"), ("PUT", "/api/patient/detail/1")):
            self.assertEqual(
                self.client.open(path, method=method, headers=self.headers).status_code, 405
            )

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

    def test_edit_and_undo_preserve_ids_timestamps_and_relations(self):
        patient = self.patient(name="张某某", age=65, medical_history="高血压既往史")
        result = self.client.put(
            f"/api/patient/update/{patient['id']}",
            json={**patient, "age": 66},
            headers=self.headers,
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["data"]["create_time"], patient["create_time"])
        record = self.post(
            "/api/medical/add", {"patient_id": patient["id"], "diagnosis": "随访"}
        ).json["data"]
        updated = self.client.put(
            f"/api/medical/update/{record['id']}",
            json={**record, "diagnosis": "复诊"},
            headers=self.headers,
        )
        self.assertEqual(updated.json["data"]["diagnosis"], "复诊")
        receipt = self.client.delete(
            f"/api/medical/delete/{record['id']}", headers=self.headers
        ).json["data"]
        restored = self.post("/api/medical/restore", {"token": receipt["restore_token"]})
        self.assertEqual(restored.json["data"]["id"], record["id"])
        self.assertEqual(restored.json["data"]["record_time"], record["record_time"])
        self.assertEqual(
            self.post("/api/medical/restore", {"token": receipt["restore_token"]}).status_code, 410
        )
        self.assertEqual(
            self.client.delete(
                f"/api/patient/delete/{patient['id']}", headers=self.headers
            ).status_code,
            409,
        )

    def test_undo_is_scoped_to_owner_expiration_and_existing_patient(self):
        from backend.model.patient import Patient
        from backend.service.recycle_service import DeleteReceipt

        patient = self.patient()
        record = self.post("/api/medical/add", {"patient_id": patient["id"]}).json["data"]
        receipt = self.client.delete(
            f"/api/medical/delete/{record['id']}", headers=self.headers
        ).json["data"]
        with self.app.app_context():
            db.session.get(DeleteReceipt, receipt["restore_token"]).user_id = 999
            db.session.commit()
        self.assertEqual(
            self.post("/api/medical/restore", {"token": receipt["restore_token"]}).status_code, 410
        )
        with self.app.app_context():
            db.session.get(DeleteReceipt, receipt["restore_token"]).user_id = 1
            db.session.delete(db.session.get(Patient, patient["id"]))
            db.session.commit()
        self.assertEqual(
            self.post("/api/medical/restore", {"token": receipt["restore_token"]}).status_code, 409
        )
        with self.app.app_context():
            db.session.get(DeleteReceipt, receipt["restore_token"]).expires_at = (
                datetime.now() - timedelta(seconds=1)
            )
            db.session.commit()
        self.assertEqual(
            self.post("/api/medical/restore", {"token": receipt["restore_token"]}).status_code, 410
        )

    def test_patient_undo_preserves_original_archive(self):
        patient = self.patient(name="张某某", phone="13800000001", medical_history="高血压")
        receipt = self.client.delete(
            f"/api/patient/delete/{patient['id']}", headers=self.headers
        ).json["data"]
        restored = self.post("/api/patient/restore", {"token": receipt["restore_token"]})
        self.assertEqual(restored.json["data"], patient)

    def test_analytics_use_database_and_fill_empty_dates(self):
        patient = self.patient(age=65)
        self.patient(age=None)
        self.post("/api/medical/add", {"patient_id": patient["id"]})
        result = self.client.get("/api/user/analytics?days=7", headers=self.headers).json["data"]
        self.assertEqual(result["patientCount"], 2)
        self.assertEqual(result["periodRecords"], 1)
        self.assertEqual(result["averageAge"], 65)
        self.assertEqual(len(result["trend"]), 7)
        self.assertEqual([item["value"] for item in result["trend"]], [0, 0, 0, 0, 0, 0, 1])
        self.assertEqual(sum(item["value"] for item in result["ageDistribution"]), 2)
        for value in ("91", "-1", "1.5", "abc"):
            self.assertEqual(
                self.client.get(
                    f"/api/user/analytics?days={value}", headers=self.headers
                ).status_code,
                400,
            )

    def test_chat_stream_delivers_events_before_model_finishes_and_masks_errors(self):
        def events(_):
            yield {"type": "delta", "content": "部分回答"}
            raise RuntimeError("sk-SECRET-EXAMPLE")

        with patch("backend.controller.rag_controller.RagService.stream_chat", side_effect=events):
            response = self.client.post(
                "/api/rag/chat-stream",
                json={"question": "资料是什么"},
                headers=self.headers,
                buffered=False,
            )
            iterator = iter(response.response)
            self.assertIn("部分回答", next(iterator).decode())
            failure = next(iterator).decode()
            self.assertIn('"type": "error"', failure)
            self.assertNotIn("SECRET", failure)
            response.close()

    def test_stream_upload_reports_actual_phases_and_parser_failure(self):
        def events(text, source):
            self.assertEqual(text, "测试资料")
            self.assertEqual(source, "测试.txt")
            yield {"type": "progress", "stage": "vectorizing"}
            yield {"type": "done", "result": {"added": 1, "total": 1}}

        with patch(
            "backend.controller.rag_controller.RagService.stream_upload", side_effect=events
        ):
            response = self.client.post(
                "/api/rag/upload-stream",
                headers=self.headers,
                data={"file": (io.BytesIO("测试资料".encode()), "测试.txt")},
            )
            body = response.get_data(as_text=True)
            self.assertLess(body.index('"parsing"'), body.index('"vectorizing"'))
            self.assertIn('"type": "done"', body)
        response = self.client.post(
            "/api/rag/upload-stream",
            headers=self.headers,
            data={"file": (io.BytesIO(b"broken pdf"), "test.pdf")},
        )
        body = response.get_data(as_text=True)
        self.assertIn('"type": "error"', body)
        self.assertNotIn('"type": "done"', body)


if __name__ == "__main__":
    unittest.main()
