"""患者管理接口。"""

from flask import Blueprint, jsonify

from backend.service.patient_service import PatientService
from backend.utils.response import success
from backend.utils.validation import ApiError, integer_field, json_body, text_field

patient_bp = Blueprint("patient", __name__)


@patient_bp.route("/list", methods=["GET"])
def list_patient():
    return jsonify(success(PatientService.list_patient(), "查询成功"))


@patient_bp.route("/add", methods=["POST"])
def add_patient():
    data = json_body()
    fields = {
        "name": text_field(data, "name", "患者姓名", 50, required=True),
        "patient_no": text_field(data, "patient_no", "患者编号", 50),
        "gender": text_field(data, "gender", "性别", 10),
        "age": integer_field(data, "age", "年龄"),
        "phone": text_field(data, "phone", "电话", 20),
        "address": text_field(data, "address", "地址", 255),
        "medical_history": text_field(data, "medical_history", "既往病史", 20000),
    }
    if fields["gender"] not in ("", "男", "女", "其他", "未知"):
        raise ApiError("性别值不支持")
    return jsonify(success(PatientService.add_patient(fields), "新增患者成功"))


@patient_bp.route("/delete/<int:id>", methods=["DELETE"])
def delete_patient(id):
    if not PatientService.delete_patient(id):
        raise ApiError("患者不存在", 404)
    return jsonify(success(None, "删除成功"))
