"""
用户表模型
"""


from backend.config.database import db



class User(db.Model):


    __tablename__="sys_user"



    id=db.Column(

        db.BigInteger().with_variant(db.Integer, "sqlite"),

        primary_key=True

    )


    username=db.Column(

        db.String(50),

        unique=True,

        nullable=False

    )



    password=db.Column(

        db.String(255),

        nullable=False

    )



    real_name=db.Column(

        db.String(50)

    )



    role=db.Column(

        db.String(20)

    )



    phone=db.Column(

        db.String(20)

    )



    status=db.Column(

        db.Integer,

        default=1

    )



    create_time=db.Column(

        db.DateTime,

        server_default=db.func.now()

    )



    def to_dict(self):


        return {


            "id":self.id,

            "username":self.username,

            "real_name":self.real_name,

            "role":self.role,

            "phone":self.phone

        }
