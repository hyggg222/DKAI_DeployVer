import cv2
import threading
import time
import os
import numpy as np

class CameraStream:
    def __init__(self, source, name="Camera", loop=True):
        self.source = source
        self.name = name
        self.loop = loop
        self.stopped = False
        self.frame = None
        self.lock = threading.Lock()
        self.finished = False

        self.is_file = isinstance(source, str) and os.path.exists(source)
        if self.is_file:
            mode_desc = "LOOPING" if self.loop else "ONE-SHOT"
            print(f"[{name}] Mode: VIDEO FILE ({mode_desc})")
        else:
            print(f"[{name}] Mode: LIVE STREAM")

        self.stream = cv2.VideoCapture(self.source)
        self.frame = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(self.frame, "LOADING...", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        if not self.stream.isOpened():
            print(f"[{name}] Error: Cannot open source {self.source}!")
            self.stopped = True

        self.fps = self.stream.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0 or self.fps > 120:
            self.fps = 30

    def start(self):
        t = threading.Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        while True:
            if self.stopped:
                return

            if self.finished:
                time.sleep(0.1)
                continue

            if self.is_file:
                time.sleep(1 / self.fps)

            grabbed, frame = self.stream.read()

            if not grabbed:
                if self.is_file:
                    if self.loop:
                        self.stream.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        print(f"[{self.name}] End of video. Stopped.")
                        self.finished = True
                        continue
                else:
                    self.stream.release()
                    time.sleep(2)
                    self.stream = cv2.VideoCapture(self.source)
                    continue

            with self.lock:
                self.frame = frame

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else np.zeros((360, 640, 3), dtype=np.uint8)

    def stop(self):
        self.stopped = True
        self.stream.release()

class DualCameraSystem:
    def __init__(self, source_front, source_back, loop=True):
        self.cam_front = CameraStream(source_front, name="Front-Cam", loop=loop)
        self.cam_back = CameraStream(source_back, name="Back-Cam", loop=loop)

    def start(self):
        self.cam_front.start()
        self.cam_back.start()

    def stop(self):
        self.cam_front.stop()
        self.cam_back.stop()

    def get_frames(self):
        return self.cam_front.read(), self.cam_back.read()
