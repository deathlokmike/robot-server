from fastapi import APIRouter, Request

from app.services.image_processor import ImageProcessor

router = APIRouter(prefix="/api", tags=["Image processing"])


@router.post("/image")
async def input_request(request: Request):
    image_raw_bytes = await request.body()
    await ImageProcessor.find_person_and_notify_all(image_raw_bytes)
    return {"status": "image received"}
