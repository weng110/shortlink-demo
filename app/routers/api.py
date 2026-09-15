"""REST API：创建 / 列表 / 统计 / 禁用 短链。"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CreateLinkRequest, CreateLinkResponse, LinkResponse
from ..services import link_service

router = APIRouter(tags=["links"])


@router.post("/links", response_model=CreateLinkResponse, summary="创建短链")
def create_link(request: Request, body: CreateLinkRequest, db: Session = Depends(get_db)):
    link = link_service.create_link(db, body.long_url)
    short_url = f"{str(request.base_url).rstrip('/')}/s/{link.short_code}"
    return CreateLinkResponse(code=link.short_code, short_url=short_url, long_url=link.long_url)


@router.get("/links", summary="短链列表（含实时点击量）")
def list_links(db: Session = Depends(get_db)):
    return link_service.list_links(db)


@router.get("/links/{code}/stats", response_model=LinkResponse, summary="单个短链统计")
def get_stats(code: str, request: Request, db: Session = Depends(get_db)):
    stats = link_service.get_stats(db, code)
    if not stats:
        raise HTTPException(status_code=404, detail="短链不存在")
    stats["short_url"] = f"{str(request.base_url).rstrip('/')}/s/{code}"
    return stats


@router.delete("/links/{code}", summary="禁用短链")
def disable_link(code: str, db: Session = Depends(get_db)):
    link = link_service.disable_link(db, code)
    return {"code": link.short_code, "status": "disabled"}


@router.get("/health", summary="健康检查（Docker Compose 探活用）")
def health(db: Session = Depends(get_db)):
    db.execute(__import__("sqlalchemy").text("SELECT 1"))
    return {"status": "ok"}
