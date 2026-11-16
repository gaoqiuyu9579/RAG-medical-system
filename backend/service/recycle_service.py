"""删除回执与短时撤销，与业务删除在同一事务中保存。"""

import secrets
from datetime import datetime, timedelta

from flask import g

from backend.config.database import db
from backend.model.medical_record import MedicalRecord
from backend.model.patient import Patient
from backend.utils.validation import ApiError


class DeleteReceipt(db.Model):
    __tablename__ = "delete_receipt"

    token = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.BigInteger, nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)


def remember_deleted(item, kind):
    now = datetime.now()
    DeleteReceipt.query.filter(DeleteReceipt.expires_at < now).delete()
    receipt = DeleteReceipt(
        token=secrets.token_hex(24),
        user_id=g.current_user.id,
        kind=kind,
        payload=item.to_dict(),
        expires_at=now + timedelta(seconds=30),
    )
    db.session.add(receipt)
    return {"restore_token": receipt.token, "undo_seconds": 30}


def restore_deleted(token, kind):
    receipt = (
        DeleteReceipt.query.filter_by(token=token, kind=kind, user_id=g.current_user.id)
        .with_for_update()
        .first()
    )
    if receipt is None or receipt.expires_at < datetime.now():
        raise ApiError("撤销已过期或记录已恢复，请刷新列表", 410)
    fields = dict(receipt.payload)
    model = Patient if kind == "patient" else MedicalRecord
    if db.session.get(model, fields["id"]) is not None:
        raise ApiError("原编号已被占用，无法撤销，请刷新后核对", 409)
    if kind == "patient":
        if Patient.query.filter_by(patient_no=fields["patient_no"]).first():
            raise ApiError("患者编号已被占用，无法撤销", 409)
        time_field = "create_time"
    else:
        patient = Patient.query.filter_by(id=fields["patient_id"]).with_for_update().first()
        if patient is None:
            raise ApiError("关联患者已被删除，请先恢复患者", 409)
        time_field = "record_time"
    if fields.get(time_field):
        fields[time_field] = datetime.fromisoformat(fields[time_field])
    item = model(**fields)
    db.session.add(item)
    db.session.delete(receipt)
    db.session.commit()
    return item.to_dict()
