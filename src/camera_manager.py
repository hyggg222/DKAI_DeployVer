import cv2
import threading
import time
import os
import numpy as np

class CameraStream:
    def __init__(self, source, name="Camera"):
        self.source = source
        self.name = name
        self.stopped = False
        self.frame = None
        self.lock = threading.Lock()
        
        # Thêm biến này để biết video đã hết chưa
        self.finished = False 
        
        # Kiểm tra nguồn là File hay Live
        self.is_file = isinstance(source, str) and os.path.exists(source)
        if self.is_file:
            print(f"[{name}] Mode: VIDEO FILE (ONE-SHOT)") # Đổi tên mode
        else:
            print(f"[{name}] Mode: LIVE STREAM")

        self.stream = cv2.VideoCapture(self.source)
        
        # Tạo ảnh đen chờ sẵn
        self.frame = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(self.frame, "LOADING...", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        if not self.stream.isOpened():
            print(f"[{name}] LỖI: Không mở được nguồn!")
            self.stopped = True

        self.fps = self.stream.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0 or self.fps > 120: self.fps = 30

    def start(self):
        t = threading.Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        while True:
            if self.stopped: return

            # Nếu video đã hết, ngủ đông (giữ nguyên frame cuối)
            if self.finished:
                time.sleep(0.1)
                continue

            if self.is_file:
                time.sleep(1 / self.fps) # Giả lập FPS thực

            grabbed, frame = self.stream.read()

            if not grabbed:
                if self.is_file:
                    # >>> SỬA Ở ĐÂY: KHÔNG TUA LẠI NỮA <<<
                    print(f"[{self.name}] Đã hết video. Dừng tại frame cuối.")
                    self.finished = True # Đánh dấu đã xong
                    continue 
                else:
                    # Nếu là Live stream mà mất tín hiệu thì thử kết nối lại
                    self.stream.release()
                    time.sleep(2)
                    self.stream = cv2.VideoCapture(self.source)
                    continue

            with self.lock:
                self.frame = frame

    def read(self):
        with self.lock:
            # Luôn trả về ảnh (kể cả khi finished, nó sẽ trả về frame cuối cùng)
            return self.frame.copy() if self.frame is not None else np.zeros((360, 640, 3), dtype=np.uint8)

    def stop(self):
        self.stopped = True
        self.stream.release()

class DualCameraSystem:
    def __init__(self, source_front, source_back):
        self.cam_front = CameraStream(source_front, name="Front-Cam")
        self.cam_back = CameraStream(source_back, name="Back-Cam")

    def start(self):
        self.cam_front.start()
        self.cam_back.start()

    def stop(self):
        self.cam_front.stop()
        self.cam_back.stop()

    def get_frames(self):
        return self.cam_front.read(), self.cam_back.read()