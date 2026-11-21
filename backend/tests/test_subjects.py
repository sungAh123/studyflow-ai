import pytest


def body(name="운영체제", day="월", start="09:00", end="10:30"):
    return {"subject_name": name, "day": day, "start_time": start, "end_time": end}


def test_endpoints_require_login(anon_client):
    assert anon_client.get("/api/subjects").status_code == 401
    assert anon_client.get("/api/timetables").status_code == 401
    assert anon_client.post("/api/timetables", json=body()).status_code == 401
    assert anon_client.put("/api/timetables/1", json=body()).status_code == 401
    assert anon_client.delete("/api/timetables/1").status_code == 401


def test_create_timetable_creates_subject(client):
    res = client.post("/api/timetables", json=body())
    assert res.status_code == 201
    assert res.json()["day"] == "월"

    subjects = client.get("/api/subjects").json()
    assert [s["name"] for s in subjects] == ["운영체제"]


def test_same_subject_on_multiple_days_is_one_subject(client):
    client.post("/api/timetables", json=body(day="월"))
    client.post("/api/timetables", json=body(day="수"))

    assert len(client.get("/api/subjects").json()) == 1
    assert len(client.get("/api/timetables").json()) == 2


def test_subject_name_is_stripped_before_dedup(client):
    client.post("/api/timetables", json=body(name=" 운영체제 "))
    client.post("/api/timetables", json=body(name="운영체제", day="수"))

    subjects = client.get("/api/subjects").json()
    assert [s["name"] for s in subjects] == ["운영체제"]


@pytest.mark.parametrize(
    "payload",
    [
        body(day="월요일"),
        body(start="25:00"),
        body(end="9:00"),
        body(name=""),
    ],
)
def test_invalid_input_is_rejected(client, payload):
    assert client.post("/api/timetables", json=payload).status_code == 422


def test_whitespace_only_name_is_rejected(client):
    assert client.post("/api/timetables", json=body(name="   ")).status_code == 422


def test_update_timetable(client):
    created = client.post("/api/timetables", json=body()).json()

    res = client.put(
        f"/api/timetables/{created['id']}",
        json=body(name="데이터베이스", day="화", start="13:00", end="14:30"),
    )
    assert res.status_code == 200
    assert res.json()["day"] == "화"
    assert res.json()["start_time"] == "13:00"

    # 과목명을 바꾸면 새 과목이 생기고, 기존 과목은 남는다.
    names = sorted(s["name"] for s in client.get("/api/subjects").json())
    assert names == ["데이터베이스", "운영체제"]


def test_update_missing_timetable_returns_404(client):
    assert client.put("/api/timetables/9999", json=body()).status_code == 404


def test_delete_timetable_keeps_subject(client):
    created = client.post("/api/timetables", json=body()).json()

    assert client.delete(f"/api/timetables/{created['id']}").status_code == 204
    assert client.get("/api/timetables").json() == []
    assert len(client.get("/api/subjects").json()) == 1


def test_delete_missing_timetable_returns_404(client):
    assert client.delete("/api/timetables/9999").status_code == 404


def test_users_cannot_see_or_modify_each_others_timetables(client, make_client):
    other = make_client(notion_user_id="notion-user-2", name="김철수")
    created = client.post("/api/timetables", json=body()).json()

    assert other.get("/api/timetables").json() == []
    assert other.get("/api/subjects").json() == []
    assert other.put(f"/api/timetables/{created['id']}", json=body(day="화")).status_code == 404
    assert other.delete(f"/api/timetables/{created['id']}").status_code == 404

    mine = client.get("/api/timetables").json()
    assert len(mine) == 1
    assert mine[0]["day"] == "월"


def test_same_subject_name_is_allowed_for_different_users(client, make_client):
    other = make_client(notion_user_id="notion-user-2")

    a = client.post("/api/timetables", json=body()).json()
    b = other.post("/api/timetables", json=body()).json()

    assert a["subject_id"] != b["subject_id"]