"""外部 Embedding 客户端配置。"""

from flask import current_app
from langchain_openai import OpenAIEmbeddings

from backend.utils.validation import ApiError


def get_embedding():
    key = current_app.config["DASHSCOPE_API_KEY"]
    if not key:
        raise ApiError("向量服务未配置，请填写 DASHSCOPE_API_KEY", 503)
    return OpenAIEmbeddings(
        api_key=key,
        base_url=current_app.config["DASHSCOPE_BASE_URL"],
        model="text-embedding-v3",
        tiktoken_enabled=False,
        check_embedding_ctx_length=False,
        chunk_size=10,
        request_timeout=45,
        max_retries=1,
    )
