"""核心闭环测试：创建 -> 跳转 -> 计数 -> 列表 / 统计 -> 禁用 / 限流。"""


def create_link(client, long_url="https://www.baidu.com"):
    return client.post("/api/links", json={"long_url": long_url})


def test_create_link(client):
    resp = create_link(client)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"]
    assert data["short_url"].endswith(f"/s/{data['code']}")
    assert data["long_url"] == "https://www.baidu.com"


def test_create_invalid_url(client):
    assert create_link(client, "not-a-url").status_code == 400
    assert create_link(client, "").status_code == 400


def test_redirect_302(client):
    data = create_link(client).json()
    resp = client.get(f"/s/{data['code']}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://www.baidu.com"


def test_click_count_increments(client):
    data = create_link(client).json()
    for _ in range(3):
        client.get(f"/s/{data['code']}", follow_redirects=False)
    stats = client.get(f"/api/links/{data['code']}/stats").json()
    assert stats["click_count"] == 3


def test_sync_clicks_to_db(client):
    """点击先记 Redis，sync 后落库，列表实时计数仍正确。"""
    data = create_link(client).json()
    for _ in range(2):
        client.get(f"/s/{data['code']}", follow_redirects=False)

    from app.tasks import sync_clicks_once

    sync_clicks_once()

    stats = client.get(f"/api/links/{data['code']}/stats").json()
    assert stats["click_count"] == 2


def test_redirect_unknown_404(client):
    assert client.get("/s/notexist", follow_redirects=False).status_code == 404


def test_list_links(client):
    create_link(client)
    create_link(client, "https://www.bing.com")
    links = client.get("/api/links").json()
    assert len(links) == 2
    assert all("click_count" in item for item in links)


def test_disable_link(client):
    data = create_link(client).json()
    assert client.delete(f"/api/links/{data['code']}").status_code == 200
    # 禁用后跳转返回 404，缓存也被清除
    assert client.get(f"/s/{data['code']}", follow_redirects=False).status_code == 404


def test_rate_limit_429(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "rate_limit_per_min", 3)
    data = create_link(client).json()

    for _ in range(3):
        assert client.get(f"/s/{data['code']}", follow_redirects=False).status_code == 302
    assert client.get(f"/s/{data['code']}", follow_redirects=False).status_code == 429


def test_pages_and_docs(client):
    assert client.get("/").status_code == 200
    assert client.get("/dashboard").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/api/health").json() == {"status": "ok"}
