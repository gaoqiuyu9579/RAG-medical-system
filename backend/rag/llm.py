"""对话模型客户端，设置显式超时和有限重试。"""

from flask import current_app
from langchain_openai import ChatOpenAI

from backend.utils.validation import ApiError


def get_llm():
    key = current_app.config["DEEPSEEK_API_KEY"]
    if not key:
        raise ApiError("对话服务未配置，请填写 DEEPSEEK_API_KEY", 503)
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=key,
        base_url=current_app.config["DEEPSEEK_BASE_URL"],
        temperature=0.3,
        timeout=45,
        max_retries=1,
    )
