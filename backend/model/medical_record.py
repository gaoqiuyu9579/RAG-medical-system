"""
电子病历数据模型
"""


from backend.config.database import db


class MedicalRecord(db.Model):
    __tablename__ = "medical_record"

    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    patient_id = db.Column(db.BigInteger, db.ForeignKey('patient.id', ondelete='RESTRICT'), nullable=False)
    doctor_name = db.Column(db.String(50))
    diagnosis = db.Column(db.String(255))
    symptom = db.Column(db.Text)
    treatment = db.Column(db.Text)
    medicine = db.Column(db.Text)
    record_time = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "doctor_name": self.doctor_name,
            "diagnosis": self.diagnosis,
            "symptom": self.symptom,
            "treatment": self.treatment,
            "medicine": self.medicine,
            "record_time": str(self.record_time) if self.record_time else None
        }
