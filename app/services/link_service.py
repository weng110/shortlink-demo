"""短链接核心服务：创建、查询缓存、跳转计数、统计、禁用。"""

import re
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Link
from ..redis_client import redis_holder
from ..utils.base62 import encode

URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)

# Redis key 约定
CODE_KEY = "link:code:{code}"     # 短码 -> 长链接缓存
CLICK_KEY = "link:click:{code}"   # 短码 -> Redis 点击计数
DIRTY_SET = "link:click:dirty"    # 有待同步点击数的短码集合


def _redis():
    return redis_holder.get()


def code_cache_key(code: str) -> str:
    return CODE_KEY.format(code=code)


def click_cache_key(code: str) -> str:
    return CLICK_KEY.format(code=code)


def validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url or len(url) > 2048 or not URL_RE.match(url):
        raise HTTPException(status_code=400, detail="long_url 必须是合法的 http/https 链接")
    return url


def create_link(db: Session, long_url: str) -> Link:
    """创建短链：插入 MySQL 拿自增 ID -> Base62 生成短码 -> 回写 -> 写 Redis 缓存。"""
    long_url = validate_url(long_url)

    # 先用临时唯一短码占位（16 字符内），拿到自增 ID 后再生成正式短码
    link = Link(long_url=long_url, short_code=f"tmp-{uuid.uuid4().hex[:12]}")
    db.add(link)
    db.commit()
    db.refresh(link)

    code = encode(link.id)
    link.short_code = code
    db.commit()

    # 写缓存，后续 /s/{code} 命中缓存不再查库
    _redis().set(code_cache_key(code), long_url, ex=settings.cache_ttl)
    return link


def get_long_url(db: Session, code: str) -> str | None:
    """跳转用：先查 Redis，未命中再查 MySQL 并回填缓存。"""
    cached = _redis().get(code_cache_key(code))
    if cached:
        return cached

    link = db.query(Link).filter(Link.short_code == code, Link.status == 1).first()
    if link:
        _redis().set(code_cache_key(code), link.long_url, ex=settings.cache_ttl)
        return link.long_url
    return None


def incr_click(code: str) -> None:
    """点击 +1：只写 Redis 计数，由定时任务批量落库。"""
    _redis().incr(click_cache_key(code))
    _redis().sadd(DIRTY_SET, code)


def pending_clicks(code: str) -> int:
    """Redis 中尚未落库的点击量（Dashboard 实时显示用）。"""
    value = _redis().get(click_cache_key(code))
    return int(value) if value else 0


def list_links(db: Session) -> list[dict]:
    """短链列表：已落库点击量 + Redis 待落库点击量 = 实时总点击量。"""
    links = db.query(Link).order_by(Link.id.desc()).all()
    return [
        {
            "code": link.short_code,
            "long_url": link.long_url,
            "click_count": link.click_count + pending_clicks(link.short_code),
            "status": link.status,
            "created_at": link.created_at,
        }
        for link in links
    ]


def get_stats(db: Session, code: str) -> dict | None:
    link = db.query(Link).filter(Link.short_code == code).first()
    if not link:
        return None
    return {
        "code": link.short_code,
        "long_url": link.long_url,
        "click_count": link.click_count + pending_clicks(link.short_code),
        "status": link.status,
        "created_at": link.created_at,
        "updated_at": link.updated_at,
    }


def disable_link(db: Session, code: str) -> Link:
    """禁用短链：状态置 0 并清缓存。"""
    link = db.query(Link).filter(Link.short_code == code).first()
    if not link:
        raise HTTPException(status_code=404, detail="短链不存在")
    link.status = 0
    db.commit()
    _redis().delete(code_cache_key(code))
    return link
