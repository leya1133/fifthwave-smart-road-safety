
from collections import deque


class LaneMemory:
    """
    Son N karedeki tüm çizgi tespitlerini saklar ve bölgesel tutarlılığa
    göre "güvenilir" çizgileri hesaplar.
    """

    def __init__(self, memory_frames=15, cluster_tolerance_px=80, min_consistency_ratio=0.3):
        """
        Args:
            memory_frames: Kaç karelik geçmiş tutulacak (örn. 15 kare ~0.5 sn @30fps)
            cluster_tolerance_px: Aynı çizgi sayılması için X konumları arasında
                                   kabul edilebilir maksimum fark (piksel)
            min_consistency_ratio: Bir çizginin "güvenilir" sayılması için,
                                   bellekteki karelerin en az bu oranında
                                   görülmüş olması gerekir (0.3 = %30)
        """
        self.memory_frames = memory_frames
        self.cluster_tolerance_px = cluster_tolerance_px
        self.min_consistency_ratio = min_consistency_ratio
        # Her eleman: o karede tespit edilen all_lines listesi
        self.history = deque(maxlen=memory_frames)

    def update(self, all_lines_this_frame):
        """Bu karenin tespitlerini belleğe ekler."""
        self.history.append(all_lines_this_frame)

    def get_reliable_lines(self):
        """
        Bellekteki tüm kareleri analiz edip, TUTARLI ŞEKİLDE görülen
        çizgileri döndürür. Sadece 1-2 karede rastgele görülen  çizgiler elenir.

        Döndürür: [[x1,y1,x2,y2], ...] - güvenilir çizgilerin listesi
                  (her biri, o bölgedeki tüm tespitlerin ORTALAMASI alınarak
                  daha kararlı/titremesiz bir konum verir)
        """
        if not self.history:
            return []

        # 1) Tüm karelerdeki tüm çizgileri tek bir havuzda topla,
        all_observations = []  # [(frame_idx, line), ...]
        for frame_idx, lines_in_frame in enumerate(self.history):
            for line in lines_in_frame:
                all_observations.append((frame_idx, line))

        if not all_observations:
            return []

        # 2) Çizgileri X konumuna göre kümeledik (basit greedy clustering):

        clusters = []  # her cluster: {"lines": [...], "frame_indices": set()}

        for frame_idx, line in all_observations:
            line_x = (line[0] + line[2]) / 2
            matched = False

            for cluster in clusters:
                cluster_x = cluster["avg_x"]
                if abs(line_x - cluster_x) <= self.cluster_tolerance_px:
                    cluster["lines"].append(line)
                    cluster["frame_indices"].add(frame_idx)
                    # Kümenin ortalama X'ini güncelle (yeni ölçümle birlikte)
                    all_x = [(l[0] + l[2]) / 2 for l in cluster["lines"]]
                    cluster["avg_x"] = sum(all_x) / len(all_x)
                    matched = True
                    break

            if not matched:
                clusters.append({
                    "lines": [line],
                    "frame_indices": {frame_idx},
                    "avg_x": line_x,
                })

        num_frames_in_memory = len(self.history)
        reliable_lines = []

        for cluster in clusters:
            consistency_ratio = len(cluster["frame_indices"]) / num_frames_in_memory

            if consistency_ratio >= self.min_consistency_ratio:
                # Bu kümedeki tüm çizgilerin ortalamasını al -> kararlı/titremesiz çizgi
                avg_x1 = sum(l[0] for l in cluster["lines"]) / len(cluster["lines"])
                avg_y1 = sum(l[1] for l in cluster["lines"]) / len(cluster["lines"])
                avg_x2 = sum(l[2] for l in cluster["lines"]) / len(cluster["lines"])
                avg_y2 = sum(l[3] for l in cluster["lines"]) / len(cluster["lines"])
                reliable_lines.append([avg_x1, avg_y1, avg_x2, avg_y2])

        return reliable_lines

    def get_stats(self):
        """Debug/bilgi amaçlı: bellekteki durum hakkında özet."""
        total_observations = sum(len(lines) for lines in self.history)
        return {
            "frames_in_memory": len(self.history),
            "total_raw_observations": total_observations,
            "reliable_lines_count": len(self.get_reliable_lines()),
        }


if __name__ == "__main__":
    print("✓ LaneMemory modülü hazır")

    # Basit doğrulama testi: bir çizgi 8/10 karede görülüyor (tutarlı),
    # bir başkası sadece 1/10 karede görülüyor (muhtemelen gürültü)
    memory = LaneMemory(memory_frames=10, min_consistency_ratio=0.3)

    for i in range(10):
        frame_lines = []
        if i < 8:  # tutarlı çizgi: ilk 8 karede görülüyor, X biraz titriyor
            frame_lines.append([400 + i, 1000, 400 + i, 1500])
        if i == 3:  # gürültü: sadece 1 karede rastgele görülen çizgi
            frame_lines.append([1800, 1000, 1800, 1500])
        memory.update(frame_lines)

    reliable = memory.get_reliable_lines()
    print(f"\nTest: 10 kare beslendi, güvenilir çizgi sayısı: {len(reliable)}")
    print(f"Beklenen: 1 (sadece tutarlı çizgi kalmalı, gürültü elenmeli)")
    print(f"Bulunan çizgiler: {reliable}")