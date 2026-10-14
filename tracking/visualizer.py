
import cv2
import config


def draw_vehicle(frame, bbox, label_text, box_color):
    """Bir aracın kutusunu ve etiketini çizer."""
    x1, y1, x2, y2 = bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, config.BOX_THICKNESS)

    # Etiket arka planı 
    (tw, th), baseline = cv2.getTextSize(
        label_text, cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE, config.FONT_THICKNESS
    )
    cv2.rectangle(frame, (x1, y1 - th - baseline - 6), (x1 + tw + 6, y1), box_color, cv2.FILLED)
    cv2.putText(frame, label_text, (x1 + 3, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE, config.COLOR_TEXT,
                config.FONT_THICKNESS, cv2.LINE_AA)
    return frame


def draw_lane_lines(frame, left_line, right_line):
    """Tespit edilen şerit çizgilerini çizer."""
    for line_set in (left_line, right_line):
        for x1, y1, x2, y2 in line_set:
            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), config.COLOR_LANE_LINE, 3)
    return frame


def decide_box_color(speed_violation, lane_violation_status):

    if lane_violation_status == "VAR":
        return config.COLOR_LANE_VIOLATION
    if speed_violation:
        return config.COLOR_SPEED_VIOLATION
    return config.COLOR_NORMAL


def build_label(track_id, class_name, speed_kmh, pixel_per_sec, used_fallback_scale,
                 direction_label, lane_number, speed_violation,
                 lane_violation_status, direction_changed):

    parts = [f"ID:{track_id}", class_name]

    if speed_kmh is not None:
        # used_fallback_scale=True ise başına ~ koyup "yaklaşık" olduğunu belirtiyoruz
        prefix = "~" if used_fallback_scale else ""
        parts.append(f"{prefix}{speed_kmh}km/h")
    else:
        # Buraya sadece araç henüz yeterince hareket etmediyse düşülür
        parts.append(f"{pixel_per_sec:.0f}px/s(yetersiz_veri)")

    parts.append(f"Yon:{direction_label}")

    if lane_number is not None:
        parts.append(f"S{lane_number}")

    if lane_violation_status == "VAR":
        parts.append("SeritIhlali:VAR")
    elif lane_violation_status == "YOK":
        parts.append("SeritIhlali:YOK")

    parts.append("HizIhlali:VAR" if speed_violation else "HizIhlali:YOK")

    if direction_changed:
        parts.append("YON_DEGISTI")

    return " ".join(parts)