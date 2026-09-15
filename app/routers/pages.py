"""页面路由：首页 + Dashboard。"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/", summary="首页：生成短链")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/dashboard", summary="Dashboard：列表 + 图表")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")
