"""患者业务逻辑与删除时的病历保护。"""

import uuid
from datetime import datetime

from sqlalchemy import or_

from backend.config.database import db
from backend.model.medical_record import MedicalRecord
from backend.model.patient import Patient
from backend.utils.validation import ApiError
from backend.service.recycle_service import remember_deleted


class PatientService:
    @staticmethod
    def list_patient():
        return [patient.to_dict() for patient in Patient.query.order_by(Patient.id.desc()).all()]

    @staticmethod
    def search_patient(filters, page=1, page_size=20):
        # 查询列表只读取识别患者所需的字段，地址和既往病史通过详情获取。
        query = db.session.query(
            Patient.id,
            Patient.patient_no,
            Patient.name,
            Patient.gender,
            Patient.age,
            Patient.phone,
            Patient.create_time,
        )
        if filters.get("keyword"):
            keyword = filters["keyword"]
            query = query.filter(
                or_(
                    Patient.name.contains(keyword, autoescape=True),
                    Patient.patient_no == keyword,
                    Patient.phone == keyword,
                )
            )
        if filters.get("name"):
            query = query.filter(Patient.name.contains(filters["name"], autoescape=True))
        for key in ("patient_no", "phone", "gender"):
            if filters.get(key):
                query = query.filter(getattr(Patient, key) == filters[key])
        if filters.get("age_min") is not None:
            query = query.filter(Patient.age >= filters["age_min"])
        if filters.get("age_max") is not None:
            query = query.filter(Patient.age <= filters["age_max"])

        total = query.count()
        rows = (
            query.order_by(Patient.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        )
        items = []
        for row in rows:
            item = dict(row._mapping)
            item["create_time"] = str(row.create_time) if row.create_time else None
            items.append(item)
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    @staticmethod
    def get_patient(patient_id):
        if not 0 < patient_id <= 9223372036854775807:
            raise ApiError("患者不存在", 404)
        patient = db.session.get(Patient, patient_id)
        if patient is None:
            raise ApiError("患者不存在", 404)
        return patient.to_dict()

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
        receipt = remember_deleted(patient, "patient")
        db.session.delete(patient)
        db.session.commit()
        return receipt

    @staticmethod
    def update_patient(patient_id, data):
        if patient_id > 9223372036854775807:
            raise ApiError("患者不存在", 404)
        patient = Patient.query.filter_by(id=patient_id).with_for_update().first()
        if patient is None:
            raise ApiError("患者不存在", 404)
        number = data.get("patient_no") or patient.patient_no
        if Patient.query.filter(Patient.patient_no == number, Patient.id != patient_id).first():
            raise ApiError("患者编号已存在", 409)
        for key, value in {**data, "patient_no": number}.items():
            setattr(patient, key, value)
        db.session.commit()
        return patient.to_dict()
