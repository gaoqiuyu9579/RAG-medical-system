"""自动建表、按需初始化账号，并用 Waitress 提供 HTTP 服务。"""

import os


def bootstrap_admin(app):
    """只创建缺失账号，重启容器不会覆盖已有密码。"""
    from backend.config.database import db
    from backend.model.user import User
    from backend.utils.passwords import hash_password
    from backend.utils.validation import password_field, text_field

    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not password:
        return
    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME") or "admin"
    with app.app_context():
        if User.query.filter_by(username=username).first() is None:
            text_field({"username": username}, "username", "用户名", 50, required=True)
            password_field({"password": password}, "password", new=True)
            db.session.add(
                User(
                    username=username,
                    password=hash_password(password),
                    real_name="演示管理员",
                    role="admin",
                    status=1,
                )
            )
            db.session.commit()
            print(f"已初始化演示账号 {username}", flush=True)


def main():
    from backend.app import create_app
    from waitress import serve

    app = create_app()
    bootstrap_admin(app)
    if os.getenv("BOOTSTRAP_DEMO_DATA", "0") == "1":
        from deploy.demo_data import seed_demo_data

        with app.app_context():
            if seed_demo_data():
                print("已初始化合成演示资料：12 位患者、56 份随访病历", flush=True)
    serve(app, host="0.0.0.0", port=5000, threads=4)


if __name__ == "__main__":
    main()
