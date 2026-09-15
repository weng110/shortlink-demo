"""定时任务：把 Redis 中的点击计数批量同步到 MySQL（演示 Redis 计数 + 落库）。"""

import asyncio
import logging

from .database import SessionLocal
from .models import Link
from .redis_client import redis_holder
from .services import link_service

logger = logging.getLogger(__name__)


def sync_clicks_once() -> None:
    """读一次 DIRTY_SET，把每个短码的 Redis 计数累加到 MySQL，然后清计数。"""
    r = redis_holder.get()
    codes = r.smembers(link_service.DIRTY_SET)
    if not codes:
        return

    db = SessionLocal()
    try:
        for code in codes:
            count = int(r.get(link_service.click_cache_key(code)) or 0)
            if count <= 0:
                continue
            db.query(Link).filter(Link.short_code == code).update(
                {Link.click_count: Link.click_count + count}
            )
        db.commit()
    finally:
        db.close()

    # 清空已落库的计数（极端并发下可能丢失极少计数，面试可讲：要精确可上 MQ）
    for code in codes:
        r.delete(link_service.click_cache_key(code))
    r.delete(link_service.DIRTY_SET)


async def sync_loop(interval: float) -> None:
    """后台循环，每隔 interval 秒执行一次落库同步。"""
    while True:
        try:
            await asyncio.to_thread(sync_clicks_once)
        except Exception:
            logger.exception("同步点击量失败")
        await asyncio.sleep(interval)
