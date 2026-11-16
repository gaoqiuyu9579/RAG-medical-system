"""登录、当前用户、密码修改和首页统计接口。"""

from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from backend.config.database import db
from backend.model.medical_record import MedicalRecord
from backend.model.patient import Patient
from backend.service.user_service import UserService
from backend.utils.jwt_util import create_token
from backend.utils.response import success
from backend.utils.validation import ApiError, integer_field, json_body, password_field, text_field

user_bp = Blueprint("user", __name__)


@user_bp.route("/login", methods=["POST"])
def login():
    data = json_body()
    username = text_field(data, "username", "用户名", maximum=50, required=True)
    password = password_field(data, "password")
    user = UserService.login(username, password)
    if user is None:
        raise ApiError("账号密码错误或账号已停用", 401)
    token = create_token(user.id, user.password)
    return jsonify(success({"token": token, "user": user.to_dict()}, "登录成功"))


@user_bp.route("/me", methods=["GET"])
def current_user():
    return jsonify(success(g.current_user.to_dict()))


@user_bp.route("/password", methods=["POST"])
def change_password():
    data = json_body()
    old_password = password_field(data, "old_password", "原密码")
    new_password = password_field(data, "new_password", "新密码", new=True)
    UserService.change_password(g.current_user, old_password, new_password)
    return jsonify(success(None, "密码已修改，请重新登录"))


@user_bp.route("/list", methods=["GET"])
def user_list():
    if g.current_user.role != "admin":
        raise ApiError("没有访问用户列表的权限", 403)
    return jsonify(success(UserService.get_users()))


@user_bp.route("/stats", methods=["GET"])
def stats():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    return jsonify(
        success(
            {
                "patientCount": db.session.query(func.count(Patient.id)).scalar(),
                "recordCount": db.session.query(func.count(MedicalRecord.id)).scalar(),
                "todayVisit": db.session.query(func.count(MedicalRecord.id))
                .filter(
                    MedicalRecord.record_time >= today,
                    MedicalRecord.record_time < tomorrow,
                )
                .scalar(),
            }
        )
    )


@user_bp.get("/analytics")
def analytics():
    days = integer_field(request.args, "days", "统计天数", minimum=1, maximum=90) or 30
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)
    ages = [value for (value,) in db.session.query(Patient.age).all()]
    groups = [
        ("0–17 岁", 0, 17),
        ("18–44 岁", 18, 44),
        ("45–59 岁", 45, 59),
        ("60–74 岁", 60, 74),
        ("75 岁及以上", 75, 150),
    ]
    age_distribution = [
        {"name": label, "value": sum(age is not None and low <= age <= high for age in ages)}
        for label, low, high in groups
    ]
    age_distribution.append(
        {"name": "未填写/待核对", "value": sum(age is None or not 0 <= age <= 150 for age in ages)}
    )
    counts = dict(
        db.session.query(func.date(MedicalRecord.record_time), func.count(MedicalRecord.id))
        .filter(
            MedicalRecord.record_time >= start,
            MedicalRecord.record_time < today + timedelta(days=1),
        )
        .group_by(func.date(MedicalRecord.record_time))
        .all()
    )
    counts = {str(day): count for day, count in counts.items()}
    trend = [
        {
            "date": (start + timedelta(days=offset)).date().isoformat(),
            "value": counts.get((start + timedelta(days=offset)).date().isoformat(), 0),
        }
        for offset in range(days)
    ]
    known = [age for age in ages if age is not None and 0 <= age <= 150]
    return jsonify(
        success(
            {
                "patientCount": len(ages),
                "recordCount": db.session.query(func.count(MedicalRecord.id)).scalar(),
                "periodRecords": sum(item["value"] for item in trend),
                "averageAge": round(sum(known) / len(known)) if known else 0,
                "ageDistribution": age_distribution,
                "trend": trend,
            }
        )
    )
