"""患者管理接口。"""

from flask import Blueprint, jsonify, request

from backend.service.patient_service import PatientService
from backend.service.recycle_service import restore_deleted
from backend.utils.response import success
from backend.utils.validation import ApiError, integer_field, json_body, text_field

patient_bp = Blueprint("patient", __name__)


@patient_bp.route("/list", methods=["GET"])
def list_patient():
    return jsonify(success(PatientService.list_patient(), "查询成功"))


@patient_bp.get("/search")
def search_patient():
    allowed = {
        "keyword",
        "name",
        "patient_no",
        "phone",
        "gender",
        "age_min",
        "age_max",
        "page",
        "page_size",
    }
    for key, values in request.args.lists():
        if key not in allowed:
            raise ApiError(f"不支持的查询参数：{key}")
        if len(values) != 1:
            raise ApiError(f"查询参数不能重复：{key}")

    fields = {
        "keyword": text_field(request.args, "keyword", "检索关键词", 50),
        "name": text_field(request.args, "name", "患者姓名", 50),
        "patient_no": text_field(request.args, "patient_no", "患者编号", 50),
        "phone": text_field(request.args, "phone", "电话", 20),
        "gender": text_field(request.args, "gender", "性别", 10),
    }
    if fields["gender"] not in ("", "男", "女", "其他", "未知"):
        raise ApiError("性别值不支持")
    # 先限制数字文本长度，避免超长整数触发转换异常。
    numbers = {
        key: text_field(request.args, key, label, 10)
        for key, label in (
            ("age_min", "最小年龄"),
            ("age_max", "最大年龄"),
            ("page", "页码"),
            ("page_size", "每页条数"),
        )
    }
    fields["age_min"] = integer_field(numbers, "age_min", "最小年龄")
    fields["age_max"] = integer_field(numbers, "age_max", "最大年龄")
    if (
        fields["age_min"] is not None
        and fields["age_max"] is not None
        and fields["age_min"] > fields["age_max"]
    ):
        raise ApiError("最小年龄不能大于最大年龄")
    page = integer_field(numbers, "page", "页码", minimum=1, maximum=2147483647) or 1
    page_size = integer_field(numbers, "page_size", "每页条数", minimum=1, maximum=100) or 20
    return jsonify(success(PatientService.search_patient(fields, page, page_size), "查询成功"))


@patient_bp.get("/detail/<int:id>")
def patient_detail(id):
    return jsonify(success(PatientService.get_patient(id), "查询成功"))


@patient_bp.route("/add", methods=["POST"])
def add_patient():
    return jsonify(success(PatientService.add_patient(patient_fields()), "新增患者成功"))


def patient_fields():
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
    return fields


@patient_bp.put("/update/<int:id>")
def update_patient(id):
    return jsonify(success(PatientService.update_patient(id, patient_fields()), "修改患者成功"))


@patient_bp.post("/restore")
def restore_patient():
    token = text_field(json_body(), "token", "撤销凭证", 64, required=True)
    return jsonify(success(restore_deleted(token, "patient"), "患者已恢复"))


@patient_bp.route("/delete/<int:id>", methods=["DELETE"])
def delete_patient(id):
    receipt = PatientService.delete_patient(id)
    if not receipt:
        raise ApiError("患者不存在", 404)
    return jsonify(success(receipt, "删除成功"))
