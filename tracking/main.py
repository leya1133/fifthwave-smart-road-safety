
import cv2
import time

import config
from vehicle_detector import VehicleDetector
from tracker import VehicleTracker
from lane_detector import LaneDetector
from lane_memory import LaneMemory
from trajectory_manager import TrajectoryManager
from speed_estimator import estimate_speed, is_speed_violation
from direction_estimator import calculate_direction_angle, get_direction_label, detect_direction_change
from lane_manager import LaneManager
from visualizer import draw_vehicle, draw_lane_lines, decide_box_color, build_label


def process_video(video_path, output_path, model_path, lane_model_path=None):

    detector = VehicleDetector(model_path)
    tracker = VehicleTracker()
    lane_detector = LaneDetector(use_model=lane_model_path is not None,
                                  model_path=lane_model_path or "lane_model.pt")
    lane_memory = LaneMemory(memory_frames=15, cluster_tolerance_px=80,
                              min_consistency_ratio=0.3)
    trajectory_manager = TrajectoryManager()
    lane_manager = LaneManager(lane_count=2)

    speed_history = {}
    previous_angles = {}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Video acilamadi: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or config.DEFAULT_FPS
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_index = 0
    start_time = time.time()

    print(f"Video isleniyor: {video_path} (fps={fps:.1f}, boyut={width}x{height}, "
          f"toplam_kare={total_frames})")
    print(f"Lane modeli: {'AKTIF -> ' + lane_model_path if lane_model_path else 'YOK (OpenCV basit yontem kullaniliyor)'}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_index / fps

        # 1) Araçları tespit et
        detections = detector.detect(frame)

        # 2) Takip et (her araca sabit bir ID ver)
        tracks = tracker.update(frame, detections)

        # 3) ŞERİT TESPİTİ - ağır model çalıştırması BU KAREDE SADECE 1 KEZ yapılıyor
        
        raw_lines_this_frame = lane_detector.get_all_detected_lines(frame)

        # --- TEMPORAL GÜVEN ARTIRMA ---
        # Modelin güven skorları düşük olduğu için tek kareye güvenmiyoruz.
        # Son 15 karedeki tüm tespitleri belleğe ekliyoruz; bir bölgede
        # TUTARLI şekilde görülen çizgiler "güvenilir" sayılır, rastgele
        # tek seferlik tespitler (muhtemelen yanlış pozitif) elenir.
        lane_memory.update(raw_lines_this_frame)
        all_lines = lane_memory.get_reliable_lines()

    
        viz_left_line, viz_right_line = lane_detector.get_lane_lines_for_vehicle(
            all_lines, vehicle_x=width / 2
        )

        for track in tracks:
            track_id = track["track_id"]
            center = track["center"]
            bbox = track["bbox"]
            class_name = track["class_name"]

          
          
            left_line, right_line = lane_detector.get_lane_lines_for_vehicle(
                all_lines, vehicle_x=center[0]
            )

            # 4) Geçmişi güncelle
            trajectory_manager.update(track_id, center, timestamp, frame_index)
            history = trajectory_manager.get_history(track_id)

            # 5) Hız hesapla - bu aracın kendi sol/sağ çizgisiyle
            speed_result = estimate_speed(
                track_id, trajectory_manager, lane_detector, left_line, right_line,
                fps, speed_history
            )
            speed_kmh = speed_result["speed_kmh"]
            pixel_per_sec = speed_result["pixel_per_sec"]
            used_fallback_scale = speed_result["used_fallback_scale"]

            # 6) Yön hesapla (KUZEY/GUNEY/DOGU/BATI etiketleri)
            angle = calculate_direction_angle(history)
            direction_label = get_direction_label(angle)

            prev_angle = previous_angles.get(track_id)
            direction_changed = detect_direction_change(prev_angle, angle)
            previous_angles[track_id] = angle if angle is not None else prev_angle

            # 7) Şerit numarası + şerit ihlali - bu aracın kendi sol/sağ çizgisiyle
            #    (bbox de veriliyor: tek çizgi bulunduğunda aracın kendi
            #    genişliğine göre ihlal kararı verebilmek için gerekli)
            lane_number, lane_violation_status = lane_manager.update(
                track_id, center, bbox, lane_detector, left_line, right_line
            )

            speed_violation = is_speed_violation(speed_kmh)

            # 8) Çizim
            box_color = decide_box_color(speed_violation, lane_violation_status)
            label = build_label(
                track_id, class_name, speed_kmh, pixel_per_sec, used_fallback_scale,
                direction_label, lane_number, speed_violation,
                lane_violation_status, direction_changed
            )
            draw_vehicle(frame, bbox, label, box_color)

        # 9) Şerit çizgilerini ekrana çiz (görselleştirme amaçlı, genel görünüm)
        draw_lane_lines(frame, viz_left_line, viz_right_line)

        removed_ids = trajectory_manager.remove_stale_tracks(frame_index)
        for tid in removed_ids:
            speed_history.pop(tid, None)
            previous_angles.pop(tid, None)
            lane_manager.remove_track(tid)

        writer.write(frame)

        if frame_index % 30 == 0:
            elapsed_so_far = time.time() - start_time
            percent = (frame_index / total_frames * 100) if total_frames > 0 else 0
            fps_processing = frame_index / elapsed_so_far if elapsed_so_far > 0 else 0
            print(f"  Kare {frame_index}/{total_frames} (%{percent:.1f}) | "
                  f"aktif arac: {len(tracks)} | islem hizi: {fps_processing:.1f} kare/sn | "
                  f"tespit_edilen_cizgi_sayisi={len(all_lines)}")

        frame_index += 1

    cap.release()
    writer.release()

    elapsed = time.time() - start_time
    print(f"\nTamamlandi: {frame_index} kare, {elapsed:.1f} sn "
          f"(ortalama {frame_index/elapsed:.1f} kare/sn)")
    print(f"Cikti: {output_path}")


if __name__ == "__main__":

    # NOT: Bu bölümde kullanılan dosya yolları yerel bilgisayara göre tanımlanmıştır.
    # Sistemi çalıştırırken video_path, model_path ve lane_model_path değerlerini
    # kendi bilgisayarınızdaki dosya konumlarına göre güncelleyiniz.
    process_video(
    video_path=r"TestVideo.mp4",       
    output_path=r"output.mp4",             
    model_path=r"AracTespitiModeli.pt",                     
    lane_model_path=r"lane_model.pt",  
    )