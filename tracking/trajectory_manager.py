
from collections import deque
import config


class TrajectoryManager:
    def __init__(self):
        self.tracks = {}          # track_id -> deque[(x, y, timestamp)]
        self.last_seen_frame = {}  # track_id -> en son görüldüğü kare numarası

    def update(self, track_id, center, timestamp, current_frame):
        if track_id not in self.tracks:
            self.tracks[track_id] = deque(maxlen=config.HISTORY_LENGTH)

        self.tracks[track_id].append((center[0], center[1], timestamp))
        self.last_seen_frame[track_id] = current_frame

    def get_history(self, track_id):
        """[(x, y, timestamp), ...] listesi döner. Yoksa boş liste."""
        return list(self.tracks.get(track_id, []))

    def remove_stale_tracks(self, current_frame):
        """
        Belirli bir süre (config.STALE_TRACK_TIMEOUT_FRAMES) görünmeyen
        araçları hafızadan siler. Aksi halde hafıza sürekli büyür.
        """
        stale_ids = [
            tid for tid, last_frame in self.last_seen_frame.items()
            if current_frame - last_frame > config.STALE_TRACK_TIMEOUT_FRAMES
        ]
        for tid in stale_ids:
            self.tracks.pop(tid, None)
            self.last_seen_frame.pop(tid, None)
        return stale_ids

    def remove_track(self, track_id):
        self.tracks.pop(track_id, None)
        self.last_seen_frame.pop(track_id, None)