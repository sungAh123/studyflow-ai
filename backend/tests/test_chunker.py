from app.summaries.chunker import make_chunks


def test_empty_pages_make_no_chunks():
    assert make_chunks([], 100) == []
    assert make_chunks(["", ""], 100) == []


def test_short_pages_are_grouped_with_page_numbers():
    chunks = make_chunks(["첫 쪽", "둘째 쪽"], 1000)

    assert len(chunks) == 1
    assert "[1쪽]\n첫 쪽" in chunks[0]
    assert "[2쪽]\n둘째 쪽" in chunks[0]


def test_empty_page_is_skipped_but_numbering_is_kept():
    chunks = make_chunks(["첫 쪽", "", "셋째 쪽"], 1000)

    assert "[1쪽]" in chunks[0]
    assert "[2쪽]" not in chunks[0]
    assert "[3쪽]" in chunks[0]


def test_pages_are_split_into_multiple_chunks_when_over_limit():
    pages = ["가" * 80, "나" * 80, "다" * 80]

    chunks = make_chunks(pages, 100)

    assert len(chunks) == 3
    assert "[1쪽]" in chunks[0]
    assert "[3쪽]" in chunks[2]


def test_single_long_page_is_split():
    chunks = make_chunks(["가" * 250], 100)

    assert len(chunks) >= 3
    assert all("[1쪽]" in c for c in chunks)


def test_no_text_is_lost():
    pages = ["가" * 250, "나" * 130]

    joined = "".join(make_chunks(pages, 100))

    assert joined.count("가") == 250
    assert joined.count("나") == 130