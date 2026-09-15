"""简单压测脚本：并发请求指定路径，输出 QPS / P99 / 平均延迟 / 错误率。

用法：
    python scripts/load_test.py                          # 默认 http://localhost:8080 /api/links 10s 100并发
    python scripts/load_test.py http://localhost:8080 /s/2 10 100
    python scripts/load_test.py <base> <path> <秒数> <并发数>

说明：/s/{code} 跳转接口有每 IP 每分钟 60 次的限流保护，
压测该接口会先撞上限流（约 1 QPS），原始吞吐请压 /api/links 或 /api/health。
"""

import asyncio
import statistics
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
PATH = sys.argv[2] if len(sys.argv) > 2 else "/api/links"
DURATION = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
CONCURRENCY = int(sys.argv[4]) if len(sys.argv) > 4 else 100

TARGET = BASE + PATH


async def main():
    latencies: list[float] = []
    errors = 0
    rate_limited = 0
    total = 0
    deadline = time.monotonic() + DURATION

    async with httpx.AsyncClient(follow_redirects=False, timeout=10) as client:

        async def hit():
            nonlocal errors, rate_limited, total
            while time.monotonic() < deadline:
                t0 = time.perf_counter()
                try:
                    resp = await client.get(TARGET)
                    lat = (time.perf_counter() - t0) * 1000
                    latencies.append(lat)
                    if resp.status_code == 429:
                        rate_limited += 1
                    elif resp.status_code >= 500:
                        errors += 1
                except Exception:
                    errors += 1
                total += 1

        await asyncio.gather(*[hit() for _ in range(CONCURRENCY)])

    elapsed = DURATION
    qps = total / elapsed
    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99) - 1] if latencies else 0
    err_rate = errors / total * 100 if total else 0

    print("=" * 52)
    print(f"目标    : {TARGET}")
    print(f"参数    : 并发 {CONCURRENCY} / 时长 {elapsed:.0f}s")
    print(f"请求总数: {total}")
    print(f"QPS     : {qps:.1f}")
    print(f"P50     : {p50:.1f} ms")
    print(f"P95     : {p95:.1f} ms")
    print(f"P99     : {p99:.1f} ms")
    print(f"5xx错误 : {errors} ({err_rate:.2f}%)")
    print(f"429限流 : {rate_limited}")
    print("=" * 52)


if __name__ == "__main__":
    asyncio.run(main())
