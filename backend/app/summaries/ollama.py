import json

import httpx

from app.core import config


class LLMError(Exception):
    """사용자에게 그대로 보여줄 수 있는 AI 처리 실패 사유"""


def chat_json(system: str, user: str) -> dict:
    try:
        res = httpx.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2, "num_ctx": 8192},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=config.OLLAMA_TIMEOUT,
        )
        res.raise_for_status()
        return json.loads(res.json()["message"]["content"])
    except httpx.ConnectError as e:
        raise LLMError("AI 서버(Ollama)에 연결할 수 없습니다.") from e
    except httpx.TimeoutException as e:
        raise LLMError("AI 응답 시간이 초과되었습니다.") from e
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise LLMError(f"모델 {config.OLLAMA_MODEL}이(가) 설치되지 않았습니다.") from e
        raise LLMError(f"AI 서버 오류 ({e.response.status_code})") from e
    except (json.JSONDecodeError, KeyError) as e:
        raise LLMError("AI 응답을 해석하지 못했습니다. 다시 시도해 주세요.") from e