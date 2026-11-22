def make_chunks(pages: list[str], limit: int) -> list[str]:
    """쪽 번호를 붙여 limit 글자 안팎의 조각으로 묶는다. 한 쪽이 limit보다 길면 쪼갠다."""
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for no, text in enumerate(pages, start=1):
        if not text:
            continue
        for i in range(0, len(text), limit):
            part = f"[{no}쪽]\n{text[i:i + limit]}"
            if buf and size + len(part) > limit:
                chunks.append("\n\n".join(buf))
                buf, size = [], 0
            buf.append(part)
            size += len(part)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks