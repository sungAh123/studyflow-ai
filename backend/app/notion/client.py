import logging
import time
from itertools import batched

import httpx

from .blocks import BLOCKS_PER_REQUEST

logger = logging.getLogger("uvicorn.error")

API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
MAX_RETRIES = 3
AUTH_MESSAGE = "Notion 연결이 만료되었거나 해제되었습니다. 다시 로그인해 주세요."


class NotionError(Exception):
    """사용자에게 그대로 보여줄 수 있는 Notion 처리 실패 사유."""


class NotionAuthError(NotionError):
    """토큰이 만료되었거나 통합 연결이 해제됨 -> 다시 로그인 필요."""


class NotionNotFoundError(NotionError):
    """페이지가 없거나, 삭제되었거나, 공유가 해제됨."""


def _title_prop(title: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": title}}]}


def _page_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            text = "".join(t.get("plan_text", "") for t in prop.get("title", []))
            return text or "(제목 없음)"
    return "(제목 없음)"


class NotionClient:
    def __init__(self, token: str, timeout: float = 30, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(
            base_url=API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
            },
            timeout=timeout,
            transport=transport,    # 테스트에서 httpx.MockTransport를 넣는 용도
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "NotionClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


    # --- 내부 ---

    def _request(self, method: str, path: str, **kwargs) -> dict:
        res = None
        for attemp in range(MAX_RETRIES):
            try:
                res = self._http.request(method, path, **kwargs)
            except httpx.TimeoutException as e:
                raise NotionError("Notion 응답 시간이 초과되었습니다.") from e
            except httpx.HTTPError as e:
                raise NotionError("Notion에 연결할 수 없습니다.") from e

            if res.status_code == 429 and attemp < MAX_RETRIES - 1:
                time.sleep(self._retry_after(res))
                continue
            break

        if res.is_success:
            return res.json()
        self._raise(res)

    @staticmethod
    def _retry_after(res: httpx.Response) -> float:
        try:
            return min(float(res.headers.get("Retry-After", 1)), 10.0)
        except ValueError:
            return 1.0

    @staticmethod
    def _raise(res: httpx.Response) -> None:
        try:
            body = res.json()
        except ValueError:
            body = {}
        code = body.get("code", "")
        logger.error("Notion 오류 %s %s: %s", res.status_code, code, body.get("message", ""))

        if res.status_code == 401:
            raise NotionAuthError(AUTH_MESSAGE)
        if res.status_code == 404:
            raise NotionNotFoundError(
                """Notion에서 새 페이지를 찾을 수 없거나 접근 권한이 없습니다."""
            )
        if res.status_code == 403:
            raise NotionError(
                """Notion에서 이 작업을 허용하지 않습니다. 통합 권한과 공유한 페이지를 확인해 주세요."""
            )
        if res.status_code == 429:
            raise NotionError("Notion 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        if res.status_code >= 500:
            raise NotionError("Notion 서버 오류입니다. 잠시 후 다시 시도해 주세요.")
        raise NotionError(f"Notion이 요청을 거부했습니다." ({code or res.status_code}))

    # --- 연결 확인 / 페이지 검색 ---

    def me(self) -> dict:
        """토큰이 유효한지 확인한다. 유효하면 통합(봇) 정보를 돌려준다."""
        return self._request("GET", "/user/me")

    def search_pages(self, query: str = "", limit: int = 50) -> list[dict]:
        """통합이 접근할 수 있는(=사용자가 공유한) 페이지 목록. 최근 수정 순."""
        results: list[dict] = []
        cursor: str | None = None
        while len(results) < limit:
            body: dict = {
                "filter": {"property": "object", "value": "page"},
                "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                "page_size": 100,
            }
            if query:
                body["query"] = query
            if cursor:
                body["start_cursor"] = cursor
            data = self._request("POST", "/search", json=body)
            for page in data.get("results", []):
                if page.get("archived") or page.get("in_trash"):
                    continue
                results.append(
                    {"id": page["id"], "title": _page_title(page), "url":page.url("url")}
                )
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        return results[:limit]

    # --- page ---

    def get_page(self, page_id: str) -> dict:
        return self._request("GET", f"/page/{page_id}")

    def find_page(self, page_id: str) -> bool:
        """페이지가 있고 삭제(휴지통)되지 않았으면 페이지 정보를, 아니면 None 반환"""
        try:
            page = self.get_page(page_id)
        except NotionNotFoundError:
            return None
        if page.get("archived") or page.get("in_trash"):
            return None
        return page

    def page_exists(self, page_id: str) -> bool:
        return self.find_page(page_id) is not None

    @staticmethod
    def title_of(page: dict) -> str:
        return _page_title(page)
    
    def create_page(self, parent_page_id: str, title: str, children: list[dict] | None = None) -> dict:
        """블록이 100개를 넘으면 첫 100개로 만들고 나머지는 이어서 추가한다.
        이어 붙이다 실패하면 반쯤 만들어진 페이지는 보관 처리하고 오류를 그대로 올린다."""
        chunks = [list(c) for c in batched(children or  [], BLOCKS_PER_REQUEST)]
        body = {
            "parent": {"page_id": parent_page_id},
            "properties": _title_prop(title),
            "children": chunks[0] if chunks else [],
        }
        page = self._request("POST", "/pages", json=body)
        try:
            for chunk in chunks[1:]:
                self._append(page["id"], chunk)
        except NotionError:
            try:
                self.archive_page(page["id"]) 
            except NotionError:
                pass
            raise   
        return page

    def update_title(self, page_id: str, title: str) -> None:
        self._request("PATCH", f"/pages/{page_id}", json={"properties": _title_prop(title)})

    def archive_page(self, page_id: str) -> None:
        self._request("PATCH", f"/pages/{page_id}", json={"archived": True})

    # --- block ---

    def _append(self, block_id: str, blocks: list[dict]) -> None:
        self._request("PATCH", f"/blocks/{block_id}/children", json={"children": blocks})

    def append_blocks(self, block_id: str, blocks: list[dict]) -> None:
        for chunk in batched(blocks, BLOCKS_PER_REQUEST):
            self._append(block_id, list(chunk))

    def clear_children(self, block_id: str) -> None:
        """페이지 안의 블록을 모두 지운다(갱신용). 블록 하나당 요청 1번이라 개수에 비해 느리다."""
        ids: list[str] = []
        cursor: str | None = None
        while True:
            params: dict = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            data = self._request("GET", f"/blocks/{block_id}/children", params=params)
            ids.extend(b["id"] for b in data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        for block in ids: 
            self._request("DELETE", f"/blocks/{block}")