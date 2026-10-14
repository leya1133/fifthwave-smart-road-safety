# Şerit Tespiti


import cv2
import numpy as np


class LaneDetector:
    def __init__(self, use_model=False, model_path="lane_model.pt"):
        """
        use_model=True  -> kendi eğittiğin lane modeli kullanılır
        use_model=False -> basit OpenCV (Canny + Hough) yöntemi kullanılır.
        """
        self.use_model = use_model
        self.model = None

        if use_model:
            from ultralytics import YOLO
            self.model = YOLO(model_path)

    def get_all_detected_lines(self, frame):
        """
        Bu karede tespit edilen TÜM çizgi parçalarını döndürür ). Her biri [x1,y1,x2,y2] formatında.

        """
        if self.use_model and self.model:
            return self._detect_with_model(frame)
        return self._detect_with_opencv_raw(frame)

    def get_lane_lines_for_vehicle(self, all_lines, vehicle_x):
        """
        Tüm tespit edilen çizgiler arasından, BU ARACIN solundaki en yakın
        çizgiyi ve sağındaki en yakın çizgiyi seçer.

        Bu yaklaşım çok şeritli yolda da doğru çalışır: her aracın "sol/sağ
        şerit çizgisi" kendi konumuna göre belirlenir, sabit değildir.

        Args:
            all_lines: get_all_detected_lines() çıktısı
            vehicle_x: aracın merkez X koordinatı

        Döndürür: (left_line, right_line) - her biri tek bir [x1,y1,x2,y2]
                  parçasını içeren liste, ya da bulunamazsa boş liste.
        """
        best_left = None
        best_left_dist = float("inf")
        best_right = None
        best_right_dist = float("inf")

        for line in all_lines:
            x1, y1, x2, y2 = line
            line_x = (x1 + x2) / 2  # çizginin yaklaşık X konumu

            if line_x < vehicle_x:
                dist = vehicle_x - line_x
                if dist < best_left_dist:
                    best_left_dist = dist
                    best_left = line
            else:
                dist = line_x - vehicle_x
                if dist < best_right_dist:
                    best_right_dist = dist
                    best_right = line

        left_line = [best_left] if best_left else []
        right_line = [best_right] if best_right else []
        return left_line, right_line

    def get_lane_lines(self, frame):
        """
        her aracın kendi konumuna göre doğru çizgiyi seçmesi için.
        """
        all_lines = self.get_all_detected_lines(frame)
        if not all_lines:
            return [], []

        # Görselleştirme amaçlı: görüntü genişliğinin ortasına göre kabaca ayır
        frame_center_x = frame.shape[1] / 2 if frame is not None else 0
        return self.get_lane_lines_for_vehicle(all_lines, frame_center_x)

    def _detect_with_model(self, frame):
        """    Burada SADECE tüm tespit edilen çizgi parçalarını ham olarak döndürüyoruz.
        """
        try:
            results = self.model(frame, conf=0.15, verbose=False)
            all_lines = []  # [[x1,y1,x2,y2], ...] - her tespit edilen çizgi kutusu

            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    # Kutunun üst-orta noktası ve alt-orta noktası -> çizgi parçası
                    top_x = (x1 + x2) / 2
                    top_y = y1
                    bottom_x = (x1 + x2) / 2
                    bottom_y = y2
                    all_lines.append([top_x, top_y, bottom_x, bottom_y])

            return all_lines
        except Exception as e:
            print(f"  [UYARI] Lane modeli hata verdi, OpenCV'ye düşülüyor: {e}")
            return self._detect_with_opencv_raw(frame)

    def _detect_with_opencv_raw(self, frame):
        """OpenCV ile basit çizgi tespiti - ham [x1,y1,x2,y2] listesi döner."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 50, minLineLength=100, maxLineGap=10)

        all_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 - x1 == 0:
                    continue
                slope = (y2 - y1) / (x2 - x1)
                # Çok yatay çizgileri ele (şerit çizgisi olamaz, gürültüdür)
                if abs(slope) > 0.2:
                    all_lines.append([x1, y1, x2, y2])
        return all_lines

    def get_x_at_y(self, line_points, y):
        """
        Bir şerit çizgisinin belirli bir Y'deki X koordinatını bulur
        (doğrusal interpolasyon ile). Bulamazsa None döner.
        """
        for x1, y1, x2, y2 in line_points:
            if min(y1, y2) <= y <= max(y1, y2) and y2 != y1:
                x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                return int(x)
        return None

    def get_lane_width_at_y(self, left_line, right_line, y):
        """
        Belirli Y koordinatında şerit genişliğini piksel olarak döndürür.
        Bu fonksiyon hız hesabının (km/h) temelidir:
        sadece o satırdaki gerçek şerit genişliği ölçülüyor.
        """
        if not left_line or not right_line:
            return None

        left_x = self.get_x_at_y(left_line, y)
        right_x = self.get_x_at_y(right_line, y)

        if left_x is None or right_x is None:
            return None

        width = abs(right_x - left_x)
        return width if width > 0 else None