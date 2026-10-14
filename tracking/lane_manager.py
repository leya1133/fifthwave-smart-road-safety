
# Bir aracın hangi şeritte olduğunu bulur ve şeritten çıkıp çıkmadığına karar verir.

import config


def calculate_lane_boundaries(left_x, right_x, lane_count=2):
    """Sol-sağ şerit çizgisi arasını eşit parçalara böler, sınırları döner."""
    if right_x <= left_x or lane_count <= 0:
        return [left_x, right_x]
    lane_width = (right_x - left_x) / lane_count
    return [left_x + i * lane_width for i in range(lane_count + 1)]


def assign_lane_number(vehicle_x, boundaries):
    """Aracın X koordinatına göre hangi şeritte olduğunu bulur (1'den başlar)."""
    if len(boundaries) < 2:
        return None
    sorted_b = sorted(boundaries)
    for i in range(len(sorted_b) - 1):
        if sorted_b[i] <= vehicle_x <= sorted_b[i + 1]:
            return i + 1
    return None


def get_lane_violation_status(vehicle_x, left_x, right_x):
    """
    KARAR: Araç şeritten / yoldan çıkıyor mu? (HER İKİ çizgi de varsa kullanılır)
    3 olası durum döner:

        "VAR"              -> araç şerit sınırlarının dışında, ihlal tespit edildi
        "YOK"               -> araç şerit içinde, ihlal yok
        "TESPIT_EDILEMEDI"  -> şerit çizgisi görünmüyor, karar verilemedi

    left_x / right_x: o anki Y'deki sol/sağ şerit çizgisinin X koordinatı.
    """
    if left_x is None or right_x is None:
        return "TESPIT_EDILEMEDI"

    tolerance = config.LANE_VIOLATION_TOLERANCE_PX
    if vehicle_x < (left_x - tolerance) or vehicle_x > (right_x + tolerance):
        return "VAR"
    return "YOK"


def get_lane_violation_status_single_line(vehicle_x, line_x, side, vehicle_half_width_px):
    """
    KARAR (TEK ÇİZGİYLE): Bu fonksiyon, TEK bir çizgiye göre de ihlal kararı
    verebilmek için var - "her zaman 2 çizgi gerekmesin, asıl önemli olan
    ihlal var mı yok mu" isteğinizi karşılıyor.

    Mantık: Aracın kendi genişliğinin yarısını (bbox'tan hesaplanan) referans
    alıyoruz. Eğer aracın o taraftaki kenarı çizgiyi aşmışsa, ihlal sayılır.

    Args:
        vehicle_x: aracın merkez X koordinatı
        line_x: tespit edilen TEK çizginin X koordinatı (o anki Y'de)
        side: "left" veya "right" - bu çizgi aracın hangi tarafında bulundu
        vehicle_half_width_px: aracın bounding box genişliğinin yarısı
                                (aracın gerçek kenarını tahmin etmek için)

    """
    tolerance = config.LANE_VIOLATION_TOLERANCE_PX

    if side == "left":
        # Çizgi aracın solunda bulundu -> aracın SOL kenarı çizgiyi geçti mi?
        vehicle_left_edge = vehicle_x - vehicle_half_width_px
        return "VAR" if vehicle_left_edge < (line_x - tolerance) else "YOK"
    else:
        # Çizgi aracın sağında bulundu -> aracın SAĞ kenarı çizgiyi geçti mi?
        vehicle_right_edge = vehicle_x + vehicle_half_width_px
        return "VAR" if vehicle_right_edge > (line_x + tolerance) else "YOK"


def is_lane_violation(vehicle_x, left_x, right_x):
  
    return get_lane_violation_status(vehicle_x, left_x, right_x) == "VAR"


class LaneManager:
    """Her aracın son bilinen şerit numarasını hafızada tutar."""

    def __init__(self, lane_count=2):
        self.lane_count = lane_count
        self._last_known_lane = {}

    def update(self, track_id, vehicle_center, vehicle_bbox, lane_detector, left_line, right_line):
        """
        Aracın şerit numarasını günceller ve döndürür.
        Ayrıca şerit ihlali durumunu da döndürür.

        left_line/right_line: main.py'de BU KAREDE 1 kez tespit edilmiş şerit
                               çizgileri.
        vehicle_bbox: (x1, y1, x2, y2) - aracın bounding box'ı. Tek çizgi
                      senaryosunda aracın gerçek genişliğini tahmin etmek
                      için kullanılır (bkz. get_lane_violation_status_single_line).

        Döndürür: (lane_number | None, violation_status: str)
        violation_status: "VAR" | "YOK" | "TESPIT_EDILEMEDI"

        ÜÇ SENARYO:
            1) Hem sol hem sağ çizgi bulundu -> en doğru karar (iki çizgi mantığı)
            2) SADECE BİR çizgi bulundu -> yine de ihlal kararı verilir
            3) Hiç çizgi yok -> karar verilemez
        """
        x, y = vehicle_center
        x1, y1, x2, y2 = vehicle_bbox
        vehicle_half_width_px = (x2 - x1) / 2

        has_left = bool(left_line)
        has_right = bool(right_line)

        # --- SENARYO 1: iki çizgi de var -> en doğru karar ---
        if has_left and has_right:
            left_x = lane_detector.get_x_at_y(left_line, int(y))
            right_x = lane_detector.get_x_at_y(right_line, int(y))
            violation_status = get_lane_violation_status(x, left_x, right_x)

            if left_x is not None and right_x is not None:
                boundaries = calculate_lane_boundaries(left_x, right_x, self.lane_count)
                lane_number = assign_lane_number(x, boundaries)
                if lane_number is not None:
                    self._last_known_lane[track_id] = lane_number

            return self._last_known_lane.get(track_id), violation_status

        # --- SENARYO 2: sadece SOL çizgi var -> tek çizgi mantığıyla karar ver ---
        if has_left and not has_right:
            left_x = lane_detector.get_x_at_y(left_line, int(y))
            if left_x is not None:
                violation_status = get_lane_violation_status_single_line(
                    x, left_x, side="left", vehicle_half_width_px=vehicle_half_width_px
                )
                return self._last_known_lane.get(track_id), violation_status

        # --- SENARYO 2b: sadece SAĞ çizgi var -> tek çizgi mantığıyla karar ver ---
        if has_right and not has_left:
            right_x = lane_detector.get_x_at_y(right_line, int(y))
            if right_x is not None:
                violation_status = get_lane_violation_status_single_line(
                    x, right_x, side="right", vehicle_half_width_px=vehicle_half_width_px
                )
                return self._last_known_lane.get(track_id), violation_status

        # --- SENARYO 3: hiç çizgi yok -> karar verilemez ---
        return self._last_known_lane.get(track_id), "TESPIT_EDILEMEDI"

    def remove_track(self, track_id):
        self._last_known_lane.pop(track_id, None)