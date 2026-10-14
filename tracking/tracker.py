

from deep_sort_realtime.deepsort_tracker import DeepSort
import config


class VehicleTracker:
    def __init__(self):
        self.tracker = DeepSort(
            max_age=config.TRACK_MAX_AGE,
            n_init=config.TRACK_N_INIT,
        )
     
        self._last_known_class = {}

    def update(self, frame, detections):
        """
        detections: vehicle_detector.detect() çıktısı
                    [(x1, y1, x2, y2, confidence, class_name), ...]
        Döndürür: [{'track_id': int, 'bbox': (x1,y1,x2,y2), 'center': (cx,cy),
                     'class_name': str}, ...]
        """
        detections_for_tracker = []
        for x1, y1, x2, y2, conf, cls_name in detections:
            w, h = x2 - x1, y2 - y1
            detections_for_tracker.append(([x1, y1, w, h], conf, cls_name))

        raw_tracks = self.tracker.update_tracks(detections_for_tracker, frame=frame)

        results = []
        for track in raw_tracks:
            if not track.is_confirmed():
                continue

            track_id = int(track.track_id)  
            x1, y1, x2, y2 = map(int, track.to_ltrb())
            center = ((x1 + x2) // 2, (y1 + y2) // 2)

            cls_name = getattr(track, "det_class", None)
            if cls_name:
                self._last_known_class[track_id] = cls_name
            class_name = self._last_known_class.get(track_id, "vehicle")

            results.append({
                "track_id": track_id,
                "bbox": (x1, y1, x2, y2),
                "center": center,
                "class_name": class_name,
            })

        return results