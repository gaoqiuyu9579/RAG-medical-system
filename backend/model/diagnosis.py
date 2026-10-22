"""
诊疗记录模型
"""


from backend.config.database import db



class DiagnosisRecord(db.Model):


    __tablename__ = "diagnosis_record"



    id = db.Column(

        db.BigInteger,

        primary_key=True

    )



    patient_id = db.Column(

        db.BigInteger,

        nullable=False

    )



    doctor = db.Column(

        db.String(50)

    )



    department = db.Column(

        db.String(50)

    )



    content = db.Column(

        db.Text

    )



    diagnosis_date = db.Column(

        db.DateTime,

        server_default=db.func.now()

    )



    def to_dict(self):

        return {


            "id":self.id,


            "patient_id":self.patient_id,


            "doctor":self.doctor,


            "department":self.department,


            "content":self.content,


            "diagnosis_date":self.diagnosis_date


        }