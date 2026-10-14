
from ultralytics import YOLO
import config


class VehicleDetector:
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def detect(self, frame):
        """
        Bir karede araçları tespit eder.
        Döndürür: [(x1, y1, x2, y2, confidence, class_name), ...]
        """
        results = self.model(
            frame,
            conf=config.CONFIDENCE_THRESHOLD,
            iou=config.IOU_THRESHOLD,
            device=config.DEVICE,
            verbose=False
        )

        detections = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                cls_id = int(box.cls[0])

                
                if cls_id not in config.VEHICLE_CLASSES:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0])
                cls_name = self.model.names[cls_id]

                detections.append((int(x1), int(y1), int(x2), int(y2), conf, cls_name))

        return detections