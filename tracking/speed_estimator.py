
import numpy as np
import config


def euclidean_distance(p1, p2):
    """İki nokta arası piksel mesafesi."""
    return float(np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2))


def is_lane_width_valid(width):
    """Ölçülen şerit genişliği mantıklı bir aralıkta mı? (çok dar/geniş ise tracking hatasıdır)"""
    if width is None:
        return False
    return config.MIN_VALID_LANE_WIDTH_PX < width < config.MAX_VALID_LANE_WIDTH_PX


def estimate_speed(track_id, trajectory_manager, lane_detector, left_line, right_line,
                    fps, speed_history):
    """
    Bir aracın hızını hesaplar.

    Parametreler:
        track_id           : aracın kimliği
        trajectory_manager : TrajectoryManager nesnesi (aracın geçmişini verir)
        lane_detector       : LaneDetector nesnesi (sadece get_x_at_y için kullanılır)
        left_line/right_line: BU KAREDE zaten 1 kez tespit edilmiş şerit çizgileri
                               (main.py her kare için 1 kez hesaplayıp buraya veriyor;
                               PERFORMANS için kritik - eskiden burada şerit tespiti
                               her araç + her geçmiş noktası için BAŞTAN tekrar
                               çalıştırılıyordu, bu çok yavaşlığın ana sebebiydi)
        fps                 : video kare hızı
        speed_history       : {track_id: [son hızlar]} sözlüğü - smoothing için
                               main.py içinde oluşturulup buraya geçirilir

    Döndürür: dict
        {
            "speed_kmh": float | None,
            "pixel_per_sec": float,
            "lane_width_px": float | None,
            "used_fallback_scale": bool,
        }
    """
    history = trajectory_manager.get_history(track_id)

    if len(history) < 2:
        return {"speed_kmh": None, "pixel_per_sec": 0.0, "lane_width_px": None,
                "used_fallback_scale": False}

    meter_speeds = []   # her kare çiftinden hesaplanan anlık m/s değerleri
    px_speeds = []       # her kare çiftinden hesaplanan anlık px/s değerleri 
    last_lane_width = None
    used_fallback_scale = False  

    for i in range(1, len(history)):
        x1, y1, t1 = history[i - 1]
        x2, y2, t2 = history[i]

        dist_px = euclidean_distance((x1, y1), (x2, y2))

        if not (config.MIN_PIXEL_DISTANCE <= dist_px <= config.MAX_PIXEL_DISTANCE):
            continue

        dt = t2 - t1
        if dt <= 0:
            dt = 1.0 / fps  

        px_speeds.append(dist_px / dt)

        avg_y = int((y1 + y2) / 2)
        lane_width_px = lane_detector.get_lane_width_at_y(left_line, right_line, avg_y)

        if is_lane_width_valid(lane_width_px):
            # Şerit bulundu -> en doğru yöntem, dinamik ölçek kullanılır
            pixel_per_meter = lane_width_px / config.REAL_LANE_WIDTH_METERS
            dist_m = dist_px / pixel_per_meter
            meter_speeds.append(dist_m / dt)
            last_lane_width = lane_width_px
        elif config.USE_FALLBACK_SCALE_WHEN_NO_LANE:
            # Şerit YOK (örn. otopark/iç mekan) -> sabit yedek ölçekle hesaplanır.
            # Bu, gerçek şerit ölçümünden daha az hassastır ama km/h üretmeyi sağlar.
            dist_m = dist_px / config.FALLBACK_PIXELS_PER_METER
            meter_speeds.append(dist_m / dt)
            used_fallback_scale = True

    # px/s her zaman hesaplanır.
    pixel_per_sec = float(np.median(px_speeds)) if px_speeds else 0.0

    # km/h sadece en az bir geçerli şerit ölçümü varsa hesaplanır
    speed_kmh = None
    if meter_speeds:
        speed_mps = float(np.median(meter_speeds))
        speed_kmh = round(speed_mps * 3.6, 1)

    
        if speed_kmh > config.MAX_REALISTIC_SPEED_KMH:
            speed_kmh = None

    if speed_kmh is not None:
        if track_id not in speed_history:
            speed_history[track_id] = []
        speed_history[track_id].append(speed_kmh)
        if len(speed_history[track_id]) > config.SMOOTHING_WINDOW:
            speed_history[track_id].pop(0)
        speed_kmh = round(float(np.median(speed_history[track_id])), 1)

    return {
        "speed_kmh": speed_kmh,
        "pixel_per_sec": round(pixel_per_sec, 1),
        "lane_width_px": round(last_lane_width, 1) if last_lane_width else None,
        "used_fallback_scale": used_fallback_scale,  # True ise hız yedek sabit ölçekle hesaplandı
    }


def is_speed_violation(speed_kmh):

    if speed_kmh is None:
        return False
    return speed_kmh > config.SPEED_LIMIT_KMH