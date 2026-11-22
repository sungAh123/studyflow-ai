import json

import httpx
import pytest

from app.summaries import ollama


def response(status=200, content=None, body=None):
    request = httpx.Request("POST", "http://ollama/api/chat")
    if body is None:
        body = {"message": {"content": content}}
    return httpx.Response(status, json=body, request=request)


def patch_post(monkeypatch, result):
    def fake_post(url, **kwargs):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr("app.summaries.ollama.httpx.post", fake_post)


def test_returns_parsed_json(monkeypatch):
    patch_post(monkeypatch, response(content=json.dumps({"summary": "ok"})))

    assert ollama.chat_json("sys", "user") == {"summary": "ok"}


def test_sends_model_and_json_format(monkeypatch):
    sent = {}

    def fake_post(url, **kwargs):
        sent["url"] = url
        sent["json"] = kwargs["json"]
        return response(content="{}")

    monkeypatch.setattr("app.summaries.ollama.httpx.post", fake_post)

    ollama.chat_json("시스템", "사용자")

    assert sent["url"].endswith("/api/chat")
    assert sent["json"]["format"] == "json"
    assert sent["json"]["stream"] is False
    assert sent["json"]["messages"][0] == {"role": "system", "content": "시스템"}
    assert sent["json"]["messages"][1] == {"role": "user", "content": "사용자"}


@pytest.mark.parametrize(
    "error, expected",
    [
        (httpx.ConnectError("refused"), "연결할 수 없습니다"),
        (httpx.ReadTimeout("slow"), "시간이 초과"),
    ],
)
def test_network_errors_become_llm_error(monkeypatch, error, expected):
    patch_post(monkeypatch, error)

    with pytest.raises(ollama.LLMError, match=expected):
        ollama.chat_json("s", "u")


def test_missing_model_is_reported(monkeypatch):
    patch_post(monkeypatch, response(status=404, body={"error": "model not found"}))

    with pytest.raises(ollama.LLMError, match="설치되지 않았습니다"):
        ollama.chat_json("s", "u")


def test_server_error_includes_status(monkeypatch):
    patch_post(monkeypatch, response(status=500, body={"error": "boom"}))

    with pytest.raises(ollama.LLMError, match="500"):
        ollama.chat_json("s", "u")


def test_invalid_json_content_is_reported(monkeypatch):
    patch_post(monkeypatch, response(content="이건 JSON이 아님"))

    with pytest.raises(ollama.LLMError, match="해석하지 못했습니다"):
        ollama.chat_json("s", "u")


def test_unexpected_response_shape_is_reported(monkeypatch):
    patch_post(monkeypatch, response(body={"unexpected": True}))

    with pytest.raises(ollama.LLMError, match="해석하지 못했습니다"):
        ollama.chat_json("s", "u")