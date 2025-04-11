from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="static/templates")

router = APIRouter(prefix="", tags=["Frontend"])


@router.get("/", response_class=HTMLResponse)
async def get_registration_page(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        context={
            "request": request,
        },
    )
