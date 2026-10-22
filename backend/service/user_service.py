"""用户认证及账号维护。"""

from backend.config.database import db
from backend.model.user import User
from backend.utils.passwords import hash_password, is_password_hash, verify_password
from backend.utils.validation import ApiError


class UserService:
    @staticmethod
    def login(username, password):
        user = User.query.filter_by(username=username).first()
        if user is None or user.status != 1 or not verify_password(user.password, password):
            return None
        # 旧账号在首次成功登录时升级；无需重置原密码。
        if not is_password_hash(user.password):
            user.password = hash_password(password)
            db.session.commit()
        return user

    @staticmethod
    def change_password(user, old_password, new_password):
        if not verify_password(user.password, old_password):
            raise ApiError("原密码不正确", 400)
        if old_password == new_password:
            raise ApiError("新密码不能与原密码相同")
        user.password = hash_password(new_password)
        db.session.commit()

    @staticmethod
    def get_users():
        return [user.to_dict() for user in User.query.order_by(User.id).all()]

    @staticmethod
    def add_user(data):
        user = User(
            username=data["username"],
            password=hash_password(data["password"]),
            real_name=data.get("real_name"),
            role=data.get("role", "admin"),
        )
        db.session.add(user)
        db.session.commit()
        return user.to_dict()

    @staticmethod
    def delete_user(user_id):
        user = db.session.get(User, user_id)
        if user is None:
            return False
        db.session.delete(user)
        db.session.commit()
        return True
