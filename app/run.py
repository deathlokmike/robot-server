from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.controllers.images import router as image_router
from app.controllers.pages import router as pages_router
from app.controllers.websockets import router as websockets_router

app_ = FastAPI()
app_.include_router(image_router)
app_.include_router(websockets_router)
app_.include_router(pages_router)

app_.mount("/static", StaticFiles(directory="static"), name="static")
