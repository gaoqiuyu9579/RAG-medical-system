"""请求参数校验，错误统一由应用转换为 JSON 响应。"""

import re

from flask import request


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("请提交有效的 JSON 对象")
    return data


def text_field(data, key, label, maximum=255, required=False):
    value = data.get(key)
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ApiError(f"{label}必须是文本")
    value = value.strip()
    if required and not value:
        raise ApiError(f"{label}不能为空")
    if len(value) > maximum:
        raise ApiError(f"{label}不能超过{maximum}个字符")
    return value


def integer_field(data, key, label, minimum=0, maximum=150, required=False):
    value = data.get(key)
    if value is None or value == "":
        if required:
            raise ApiError(f"{label}不能为空")
        return None
    if isinstance(value, bool) or not re.fullmatch(r"-?\d+", str(value)):
        raise ApiError(f"{label}必须是整数")
    value = int(value)
    if not minimum <= value <= maximum:
        raise ApiError(f"{label}必须在{minimum}到{maximum}之间")
    return value


def password_field(data, key, label="密码", new=False):
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ApiError(f"{label}不能为空")
    if len(value) > 128 or (new and len(value) < 8):
        raise ApiError(f"{label}长度应为{'8' if new else '1'}到128个字符")
    return value
