"""电子病历接口。"""

from flask import Blueprint, jsonify

from backend.service.medical_service import MedicalService
from backend.service.recycle_service import restore_deleted
from backend.utils.response import success
from backend.utils.validation import ApiError, integer_field, json_body, text_field

medical_bp = Blueprint("medical", __name__)


@medical_bp.route("/list", methods=["GET"])
def list_record():
    return jsonify(success(MedicalService.list_record(), "查询成功"))


@medical_bp.route("/add", methods=["POST"])
def add_record():
    return jsonify(success(MedicalService.add_record(record_fields()), "病历保存成功"))


def record_fields():
    data = json_body()
    fields = {
        "patient_id": integer_field(
            data, "patient_id", "患者ID", minimum=1, maximum=9223372036854775807, required=True
        ),
        "doctor_name": text_field(data, "doctor_name", "医生姓名", 50),
        "diagnosis": text_field(data, "diagnosis", "诊断", 255),
        "symptom": text_field(data, "symptom", "症状", 20000),
        "treatment": text_field(data, "treatment", "治疗方案", 20000),
        "medicine": text_field(data, "medicine", "用药信息", 20000),
    }
    return fields


@medical_bp.put("/update/<int:id>")
def update_record(id):
    return jsonify(success(MedicalService.update_record(id, record_fields()), "病历修改成功"))


@medical_bp.post("/restore")
def restore_record():
    token = text_field(json_body(), "token", "撤销凭证", 64, required=True)
    return jsonify(success(restore_deleted(token, "medical"), "病历已恢复"))


@medical_bp.route("/delete/<int:id>", methods=["DELETE"])
def delete_record(id):
    receipt = MedicalService.delete_record(id)
    if not receipt:
        raise ApiError("病历不存在", 404)
    return jsonify(success(receipt, "删除成功"))
