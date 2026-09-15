"""基于 Redis 的简单 IP 限流：INCR + EXPIRE，固定窗口 60 秒。"""

from fastapi import HTTPException, Request

from ..config import settings
from ..redis_client import redis_holder


def check(request: Request) -> None:
    """每 IP 每分钟最多 rate_limit_per_min 次，超出返回 429。"""
    ip = request.client.host if request.client else "unknown"
    key = f"limit:ip:{ip}"

    try:
        count = redis_holder.get().incr(key)
        if count == 1:
            # 第一次请求时设置过期时间，窗口自动滑动
            redis_holder.get().expire(key, 60)
    except Exception:
        # Redis 不可用时放行，避免限流组件拖垮主链路
        return

    if count > settings.rate_limit_per_min:
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，每个 IP 每分钟最多 {settings.rate_limit_per_min} 次",
        )
