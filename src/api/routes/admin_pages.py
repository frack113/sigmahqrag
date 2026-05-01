from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/admin", tags=["admin-pages"])
templates = Jinja2Templates(directory="src/templates")

@router.get("/")
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

@router.get("/health")
async def admin_health(request: Request):
    return templates.TemplateResponse("admin/health.html", {"request": request})

@router.get("/hardware")
async def admin_hardware(request: Request):
    return templates.TemplateResponse("admin/hardware.html", {"request": request})

@router.get("/logs")
async def admin_logs(request: Request):
    return templates.TemplateResponse("admin/logs.html", {"request": request})
