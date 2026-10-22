"""病历写入前验证患者，兼容已有未声明外键的数据库。"""

from backend.config.database import db
from backend.model.medical_record import MedicalRecord
from backend.model.patient import Patient
from backend.utils.validation import ApiError


class MedicalService:
    @staticmethod
    def list_record():
        return [record.to_dict() for record in MedicalRecord.query.order_by(MedicalRecord.id.desc()).all()]

    @staticmethod
    def add_record(data):
        # 与删除患者使用同一行锁，防止并发产生孤立病历。
        patient = Patient.query.filter_by(id=data["patient_id"]).with_for_update().first()
        if patient is None:
            raise ApiError("患者不存在，请重新选择", 404)
        record = MedicalRecord(**data)
        db.session.add(record)
        db.session.commit()
        return record.to_dict()

    @staticmethod
    def delete_record(record_id):
        if record_id > 9223372036854775807:
            return False
        record = db.session.get(MedicalRecord, record_id)
        if record is None:
            return False
        db.session.delete(record)
        db.session.commit()
        return True
