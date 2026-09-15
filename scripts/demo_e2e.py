"""ShortLink Demo 端到端演示脚本。

跑通面试演示闭环：
创建短链 -> 302 跳转 -> 点击 +1 -> 列表/统计 -> Redis 计数落库 -> 禁用 -> 404

用法：
    python scripts/demo_e2e.py                 # 默认 http://localhost:8080
    python scripts/demo_e2e.py http://localhost:8080
    python scripts/demo_e2e.py http://localhost:8080 --skip-sync   # 跳过 12s 落库等待
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("http") else "http://localhost:8080"
SKIP_SYNC = "--skip-sync" in sys.argv

PASSED = 0
FAILED = 0


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """不跟随重定向，用于验证 302 状态码。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def call(method, path, body=None, follow=True):
    req = urllib.request.Request(BASE + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    handler = urllib.request.HTTPRedirectHandler if follow else NoRedirect
    opener = urllib.request.build_opener(handler)
    try:
        with opener.open(req, data=data, timeout=10) as resp:
            content = resp.read().decode()
            return resp.status, resp.headers.get("Location"), (json.loads(content) if content else None)
    except urllib.error.HTTPError as e:
        content = e.read().decode() if e.fp else ""
        try:
            payload = json.loads(content)
        except Exception:
            payload = None
        return e.code, e.headers.get("Location"), payload


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  [PASS] {name} {detail}")
    else:
        FAILED += 1
        print(f"  [FAIL] {name} {detail}")


def main():
    print("=" * 64)
    print("ShortLink Demo 端到端演示")
    print(f"目标服务: {BASE}    (同步等待: {'跳过' if SKIP_SYNC else '12s'})")
    print("=" * 64)

    # 1. 创建短链
    print("\n[1] 创建短链")
    status, _, data = call("POST", "/api/links", {"long_url": "https://www.baidu.com"})
    if status != 200:
        check("创建短链", False, f"status={status}")
        return
    code, short_url = data["code"], data["short_url"]
    check("POST /api/links", True, f"{data['long_url']} -> {short_url}")

    # 2. 302 跳转（不跟随，检查状态码与 Location）
    print("\n[2] 302 跳转")
    status, location, _ = call("GET", f"/s/{code}", follow=False)
    check("GET /s/{code} 返回 302", status == 302, f"status={status}")
    check("Location 指向百度", location == "https://www.baidu.com", f"Location={location}")

    # 3. 点击统计 +1
    print("\n[3] 点击统计")
    status, _, stats = call("GET", f"/api/links/{code}/stats")
    check("stats 接口返回", status == 200, "")
    check("点击量 = 1", stats["click_count"] == 1, f"click_count={stats['click_count']}")

    # 4. Redis 中的待落库计数
    print("\n[4] Redis 计数（未落库）")
    import redis

    r = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    redis_click = r.get(f"link:click:{code}")
    check("Redis key link:click:{code} = 1", redis_click == "1", f"redis={redis_click}")

    # 5. 定时任务落库（等待一个周期）
    print("\n[5] 定时任务落库（每 10s 同步）")
    if SKIP_SYNC:
        print("  （已跳过等待）")
    else:
        print("  等待 12 秒让同步任务执行...")
        time.sleep(12)
        redis_click = r.get(f"link:click:{code}")
        check("Redis 计数已清空", redis_click is None, f"redis={redis_click}")
        status, _, stats = call("GET", f"/api/links/{code}/stats")
        check("MySQL 已落库点击量 = 1", stats["click_count"] == 1, f"click_count={stats['click_count']}")

    # 6. 列表与图表数据源
    print("\n[6] 短链列表")
    status, _, links = call("GET", "/api/links")
    check("GET /api/links", status == 200, f"共 {len(links)} 条")
    check("列表中包含新短链", any(item["code"] == code for item in links), "")

    # 7. 禁用 -> 404
    print("\n[7] 禁用短链")
    status, _, data = call("DELETE", f"/api/links/{code}")
    check("DELETE /api/links/{code}", status == 200, f"status={data}")
    status, _, _ = call("GET", f"/s/{code}", follow=False)
    check("禁用后跳转 404", status == 404, f"status={status}")

    print("\n" + "=" * 64)
    print(f"结果: {PASSED} 通过, {FAILED} 失败")
    print("=" * 64)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
