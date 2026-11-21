import pymupdf

from app.core.config import MAX_PAGES, MIN_TEXT_CHARS


class ExtractionError(Exception):
    """사용자에게 그대로 보여줄 수 있는 추출 실패 사유"""


def extract_pages(path: str) -> list[str]:
    try:
        with pymupdf.open(path) as doc:
            if doc.needs_pass:
                raise ExtractionError("암호가 걸린 PDF는 지원하지 않습니다.")
            if doc.page_count > MAX_PAGES:
                raise ExtractionError(f"{MAX_PAGES}쪽을 초과하는 PDF는 지원하지 않습니다.")
            pages = [page.get_text("text").strip() for page in doc]
    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError("PDF를 읽을 수 없습니다.") from e

    if sum(len(p) for p in pages) < MIN_TEXT_CHARS:
        raise ExtractionError("텍스트를 추출할 수 없습니다. 스캔본 PDF는 지원하지 않습니다.")
    return pages