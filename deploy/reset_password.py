"""容器管理员交互式重设密码，不在命令或日志中显示密码。"""

import argparse
from getpass import getpass

from backend.app import create_app
from backend.config.database import db
from backend.model.user import User
from backend.utils.passwords import hash_password
from backend.utils.validation import ApiError, password_field


def main():
    parser = argparse.ArgumentParser(description="重设已有账号密码")
    parser.add_argument("username", nargs="?", default="admin")
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=args.username).first()
        if user is None:
            parser.exit(1, "账号不存在\n")
        try:
            password = password_field({"password": getpass("新密码（8到128个字符）: ")}, "password", new=True)
        except ApiError as exc:
            parser.exit(1, exc.message + "\n")
        if password != getpass("再次输入新密码: "):
            parser.exit(1, "两次密码不一致，未修改\n")
        user.password = hash_password(password)
        db.session.commit()
    print("密码已修改，旧登录凭证已失效，请重新登录。")


if __name__ == "__main__":
    main()
