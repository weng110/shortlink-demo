"""短链跳转：访问 /s/{code} -> 302 重定向 + 点击计数 + IP 限流。"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import link_service, rate_limit

router = APIRouter(tags=["redirect"])


@router.get("/s/{code}", summary="302 跳转到长链接")
def redirect_link(code: str, request: Request, db: Session = Depends(get_db)):
    # 1. 限流
    rate_limit.check(request)
    # 2. 先查 Redis 缓存，未命中查 MySQL 并回填
    long_url = link_service.get_long_url(db, code)
    if not long_url:
        raise HTTPException(status_code=404, detail="短链不存在或已禁用")
    # 3. Redis 点击计数 +1
    link_service.incr_click(code)
    # 4. 302 跳转（不用 301：301 会被浏览器缓存，统计不到后续点击）
    return RedirectResponse(url=long_url, status_code=302)
