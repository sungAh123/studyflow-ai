from pathlib import Path

RICH_TEXT_LIMIT = 2000      # 텍스트 조각 하나의 최대 글자 수
RICH_TEXT_MAX_ITEMS = 100   # 블록 하나의 텍스트 조각 최대 개수
BLOCKS_PER_REQUEST = 100    # 요청 한 번에 보낼 수 있는 블록 수
TITLE_LIMIT = 100


def split_text(text: str, limit: int = RICH_TEXT_LIMIT) -> list[str]:
    """limit 글자 이하로 자른다. 가능하면 줄바꿈, 다음으로 공백 위치에서 자른다."""
    text = text.strip()
    parts: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut].rstrip())
        text = text[:cut].lstrip()
    if text:
        parts.append(text)
    return parts


def rich_text(text: str, bold: bool = False) -> list[dict]:
    items = []
    for part in split_text(text):
        item: dict = {"type": "text", "text": {"content": part}}
        if bold:
            item["annotations"] = {"bold": "True"}
        items.append(item)
    return items


def _block(kind: str, rich: list[dict]) -> dict:
    return {"object": "block", "type": kind, kind: {"rich_text": rich[:RICH_TEXT_MAX_ITEMS]}}


def heading(text: str, level: int = 2) -> dict:
    return _block(f"heading_{level}", rich_text(text))


def paragraph(text: str) -> dict:
    return _block("paragraph", rich_text(text))


def bullet(text: str) -> dict:
    return _block("bulleted_list_item", rich_text(text)) 


def term_bullet(term: str, definition: str) -> dict:
    return _block(
        "bulleted_list_item",
        rich_text(term, bold=True) + rich_text(f": {definition}")
    )


def note_title(filename: str) -> str:
    """파일명에서 확장자를 뗀 학습 노트 제목"""
    title = Path(filename).stem.strip()[:TITLE_LIMIT]
    return title or "제목 없음"


def build_note_blocks(overview: str, sections: list[dict], terms: list[dict]) -> list[dict]:
    """요약 결과를 Notion 블록 목록으로 바꿈"""
    blocks: list[dict] = []

    if overview.strip():
        blocks.append(heading("전체 요약"))
        blocks.append(paragraph(overview))

    if sections:
        blocks.append(heading("목차별 핵심"))
        for section in sections:
            blocks.append(heading(section.get("title", "").strip() or "(제목 없음)", level=3))
            for point in section.get("points", []):
                if point.strip():
                    blocks.append(bullet(point))

    if terms: 
        blocks.append(heading("주요 용어"))
        for item in terms:
            term = item.get("term", "").strip()
            if term:
                blocks.append(term_bullet(term, item.get("definition", "").strip()))

    return blocks