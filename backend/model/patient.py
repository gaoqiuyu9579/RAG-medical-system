"""
患者模型
"""

from backend.config.database import db


class Patient(db.Model):
    __tablename__ = "patient"

    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    patient_no = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(50))
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    medical_history = db.Column(db.Text)
    create_time = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "patient_no": self.patient_no,
            "name": self.name,
            "gender": self.gender,
            "age": self.age,
            "phone": self.phone,
            "address": self.address,
            "medical_history": self.medical_history,
            "create_time": str(self.create_time) if self.create_time else None,
        }
