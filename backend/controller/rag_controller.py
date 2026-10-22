"""知识库与问答接口。外部错误不向浏览器泄露凭证或堆栈。"""

import io

import pdfplumber
from flask import Blueprint, current_app, jsonify, request
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

from backend.service.rag_service import RagService
from backend.utils.response import success
from backend.utils.validation import ApiError, json_body, text_field

rag_bp = Blueprint("rag", __name__)
ALLOWED_EXTENSIONS = (".txt", ".md", ".json", ".csv", ".pdf")


def rag_call(function):
    try:
        return function()
    except ApiError:
        raise
    except AuthenticationError:
        raise ApiError("AI 服务认证失败，请检查服务密钥及模型权限", 503) from None
    except RateLimitError:
        raise ApiError("AI 服务请求受限，请稍后重试", 503) from None
    except (APIConnectionError, APITimeoutError):
        raise ApiError("AI 服务连接超时或不可用，请稍后重试", 503) from None
    except APIStatusError:
        raise ApiError("AI 服务调用失败，请检查服务端点与模型配置", 503) from None
    except Exception as exc:
        current_app.logger.warning("RAG request failed: %s", type(exc).__name__)
        raise ApiError("知识服务暂时不可用，请检查配置或稍后重试", 503) from None


def extract_pdf_text(file):
    parts = []
    length = 0
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        if len(pdf.pages) > current_app.config["MAX_PDF_PAGES"]:
            raise ApiError("PDF 页数超过200页限制")
        for page in pdf.pages:
            text = page.extract_text() or ""
            length += len(text)
            if length > current_app.config["MAX_KNOWLEDGE_CHARS"]:
                raise ApiError("提取的文本过长，请拆分资料后上传")
            parts.append(text)
    return "\n".join(parts)


@rag_bp.route("/status", methods=["GET"])
def status():
    return jsonify(success(rag_call(RagService.status)))


@rag_bp.route("/upload", methods=["POST"])
def upload():
    text = text_field(json_body(), "text", "知识文本",
                      current_app.config["MAX_KNOWLEDGE_CHARS"], required=True)
    result = rag_call(lambda: RagService.upload_text(text))
    return jsonify(success(result, "知识库构建成功"))


@rag_bp.route("/upload-file", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ApiError("请选择要上传的文件")
    filename = file.filename.replace("\\", "/").rsplit("/", 1)[-1][:255]
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise ApiError("仅支持 .txt、.md、.json、.csv、.pdf 格式")
    try:
        text = extract_pdf_text(file) if filename.lower().endswith(".pdf") else file.read().decode("utf-8-sig")
    except ApiError:
        raise
    except UnicodeDecodeError:
        raise ApiError("文件编码不支持，请使用 UTF-8 编码") from None
    except Exception:
        raise ApiError("文件无法解析，请检查 PDF 是否损坏或加密") from None
    text = text_field({"text": text}, "text", "文件内容",
                      current_app.config["MAX_KNOWLEDGE_CHARS"], required=True)
    result = rag_call(lambda: RagService.upload_text(text, filename))
    return jsonify(success(result, "文件知识库构建成功"))


@rag_bp.route("/chat", methods=["POST"])
def chat():
    question = text_field(json_body(), "question", "问题", 2000, required=True)
    return jsonify(success(rag_call(lambda: RagService.chat(question)), "回答成功"))
