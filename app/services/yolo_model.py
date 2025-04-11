from typing import Optional

from PIL import Image, ImageDraw
from ultralytics import YOLO


class YoloModel:
    _instance: Optional["YoloModel"] = None

    def __new__(cls) -> "YoloModel":
        if cls._instance is None:
            cls._instance = super(YoloModel, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.model = YOLO("yolov8n.pt")

    @staticmethod
    def draw_rectangle(
        image: Image.Image, persons_box: list[tuple[float, float, float, float]]
    ):
        for box in persons_box:
            draw = ImageDraw.Draw(image)
            draw.rectangle(box, width=1, outline="#0000ff")

    def find_person(
        self, image: Image.Image
    ) -> list[tuple[float, float, float, float]]:
        results = self.model(image, verbose=True)
        persons_boxes: list[tuple[float, float, float, float]] = []
        for res_i in results[0]:
            class_num = int(res_i.boxes.cls.cpu())
            if class_num == 0:
                boxes = res_i.boxes.xyxy.cpu()
                persons_boxes.append(boxes.tolist()[0])
        return persons_boxes
