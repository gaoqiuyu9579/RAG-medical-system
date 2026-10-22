"""患者业务逻辑与删除时的病历保护。"""

import uuid
from datetime import datetime

from backend.config.database import db
from backend.model.medical_record import MedicalRecord
from backend.model.patient import Patient
from backend.utils.validation import ApiError


class PatientService:
    @staticmethod
    def list_patient():
        return [patient.to_dict() for patient in Patient.query.order_by(Patient.id.desc()).all()]

    @staticmethod
    def add_patient(data):
        number = data.get("patient_no") or f"P{datetime.now():%Y%m%d}{uuid.uuid4().hex[:12]}"
        if Patient.query.filter_by(patient_no=number).first() is not None:
            raise ApiError("患者编号已存在", 409)
        fields = dict(data)
        fields["patient_no"] = number
        patient = Patient(**fields)
        db.session.add(patient)
        db.session.commit()
        return patient.to_dict()

    @staticmethod
    def delete_patient(patient_id):
        if patient_id > 9223372036854775807:
            return False
        patient = Patient.query.filter_by(id=patient_id).with_for_update().first()
        if patient is None:
            return False
        if MedicalRecord.query.filter_by(patient_id=patient_id).first() is not None:
            raise ApiError("该患者仍有关联病历，请先处理病历后再删除", 409)
        db.session.delete(patient)
        db.session.commit()
        return True
