"""为空库创建合成演示资料；已有患者或病历时不写入。"""

from datetime import datetime, timedelta

from backend.config.database import db
from backend.model.medical_record import MedicalRecord
from backend.model.patient import Patient


def seed_demo_data():
    if Patient.query.count() or MedicalRecord.query.count():
        return False
    people = [
        ("张某某", "男", 65, "高血压病史 8 年，定期复诊", "高血压随访"),
        ("李某某", "女", 58, "2 型糖尿病病史 5 年", "糖尿病随访"),
        ("王某某", "男", 72, "高血压，冠心病既往史", "慢病复诊"),
        ("赵某某", "女", 46, "无特殊既往病史", "健康咨询"),
        ("刘某某", "男", 34, "过敏性鼻炎病史", "鼻炎随访"),
        ("陈某某", "女", 67, "高血压病史 6 年", "高血压随访"),
        ("孙某某", "男", 81, "高血压、糖尿病既往史", "慢病复诊"),
        ("周某某", "女", 29, "无特殊既往病史", "健康咨询"),
        ("吴某某", "男", 53, "血脂异常病史 3 年", "血脂随访"),
        ("郑某某", "女", 16, "无特殊既往病史", "健康咨询"),
        ("林某某", "女", 62, "2 型糖尿病病史 4 年", "糖尿病随访"),
        ("黄某某", "男", 43, "过敏性鼻炎病史", "鼻炎随访"),
    ]
    now = datetime.now()
    patients = []
    for index, (name, gender, age, history, _) in enumerate(people, 1):
        patient = Patient(
            patient_no=f"DEMO-{index:04d}",
            name=name,
            gender=gender,
            age=age,
            phone=f"1380000{index:04d}",
            address=f"青岛市示范社区{index}号（合成地址）",
            medical_history=history,
            create_time=now - timedelta(days=40 + index),
        )
        db.session.add(patient)
        patients.append(patient)
    db.session.flush()
    for day in range(30):
        for visit in range([1, 3, 2, 0, 4, 2, 1][day % 7]):
            index = (day + visit * 3) % len(patients)
            db.session.add(
                MedicalRecord(
                    patient_id=patients[index].id,
                    doctor_name=["王医生", "李医生", "陈医生"][visit % 3],
                    diagnosis=people[index][4],
                    symptom="常规随访，记录近期自述情况（合成）",
                    treatment="完善随访记录，按既有诊疗计划复诊（合成）",
                    medicine="按原处方核对，示例不含剂量",
                    record_time=now.replace(hour=9 + visit, minute=15) - timedelta(days=day),
                )
            )
    db.session.commit()
    return True
