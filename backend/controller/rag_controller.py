"""知识库与问答接口。外部错误不向浏览器泄露凭证或堆栈。"""

import io
import json

import pdfplumber
from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from werkzeug.datastructures import FileStorage

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
    text = text_field(
        json_body(), "text", "知识文本", current_app.config["MAX_KNOWLEDGE_CHARS"], required=True
    )
    result = rag_call(lambda: RagService.upload_text(text))
    return jsonify(success(result, "知识库构建成功"))


@rag_bp.route("/upload-file", methods=["POST"])
def upload_file():
    text, filename = read_uploaded_file()
    result = rag_call(lambda: RagService.upload_text(text, filename))
    return jsonify(success(result, "文件知识库构建成功"))


def read_uploaded_file(file=None):
    if file is None:
        file = request.files.get("file")
    if file is None or not file.filename:
        raise ApiError("请选择要上传的文件")
    filename = file.filename.replace("\\", "/").rsplit("/", 1)[-1][:255]
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise ApiError("仅支持 .txt、.md、.json、.csv、.pdf 格式")
    try:
        text = (
            extract_pdf_text(file)
            if filename.lower().endswith(".pdf")
            else file.read().decode("utf-8-sig")
        )
    except ApiError:
        raise
    except UnicodeDecodeError:
        raise ApiError("文件编码不支持，请使用 UTF-8 编码") from None
    except Exception:
        raise ApiError("文件无法解析，请检查 PDF 是否损坏或加密") from None
    text = text_field(
        {"text": text}, "text", "文件内容", current_app.config["MAX_KNOWLEDGE_CHARS"], required=True
    )
    return text, filename


@rag_bp.route("/chat", methods=["POST"])
def chat():
    question = text_field(json_body(), "question", "问题", 2000, required=True)
    return jsonify(success(rag_call(lambda: RagService.chat(question)), "回答成功"))


def event_response(events):
    def generate():
        iterator = None
        try:
            iterator = iter(rag_call(events))
            while True:
                # 将迭代期间的上游异常也转换为可展示的错误，避免流悄然中断。
                event = rag_call(lambda: next(iterator, None))
                if event is None:
                    break
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        except ApiError as exc:
            yield (
                "data: "
                + json.dumps({"type": "error", "message": exc.message}, ensure_ascii=False)
                + "\n\n"
            )
        finally:
            if iterator is not None and hasattr(iterator, "close"):
                iterator.close()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache, no-store"},
    )


@rag_bp.post("/chat-stream")
def chat_stream():
    question = text_field(json_body(), "question", "问题", 2000, required=True)
    return event_response(lambda: RagService.stream_chat(question))


@rag_bp.post("/upload-stream")
def upload_stream():
    # multipart 在返回流之前读取，确保请求体限制及文件缺失使用正常 HTTP 错误。
    is_file = request.mimetype == "multipart/form-data"
    if is_file:
        file = request.files.get("file")
        if file is None or not file.filename:
            raise ApiError("请选择要上传的文件")
        # 请求结束时 Flask 会关闭 multipart 临时文件；流中解析使用有界快照。
        file = FileStorage(stream=io.BytesIO(file.read()), filename=file.filename)
    else:
        text = text_field(
            json_body(),
            "text",
            "知识文本",
            current_app.config["MAX_KNOWLEDGE_CHARS"],
            required=True,
        )

    def events():
        yield {"type": "progress", "stage": "parsing", "message": "文档解析中 · 正在提取文本"}
        content, source = read_uploaded_file(file) if is_file else (text, "粘贴文本")
        yield from RagService.stream_upload(content, source)

    return event_response(events)
