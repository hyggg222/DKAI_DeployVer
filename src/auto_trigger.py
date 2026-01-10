import cv2
from ultralytics import YOLO
import time

class AutoTriggerSystem:
    def __init__(self, model_path, line_points, cooldown=10):
        print(f">>> [TRIGGER] Đang tải Model: {model_path}")
        self.model = YOLO(model_path)
        
        # Cấu hình vạch
        self.line_y = line_points[0][1]
        self.line_x_min = line_points[0][0]
        self.line_x_max = line_points[1][0]
        
        self.previous_bottoms = {}
        self.triggered_ids = {} 
        self.cooldown = cooldown
        
        # [QUAN TRỌNG] Biến chứa danh sách xe để vẽ lên Web
        self.latest_tracks = [] 

    def get_bottom_center(self, box):
        x1, y1, x2, y2 = map(int, box)
        return (int((x1 + x2) / 2), int(y2))

    def check(self, frame):
        now = time.time()
        # Xoá các ID đã trigger quá lâu khỏi danh sách cooldown
        self.triggered_ids = {k:v for k,v in self.triggered_ids.items() if now-v <= self.cooldown}

        # Tracking
        results = self.model.track(frame, persist=True, verbose=False, conf=0.4, tracker="bytetrack.yaml")
        
        triggered_now = (False, None)
        current_frame_ids = []
        self.latest_tracks = [] # Reset list vẽ

        if results[0].boxes.id is not None:
            # Lấy thông tin từ YOLO
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            cls_ids = results[0].boxes.cls.int().cpu().tolist()
            confs = results[0].boxes.conf.cpu().numpy()

            # 1. TẠO DANH SÁCH CÁC XE HỢP LỆ
            valid_vehicles = []
            for box, track_id, cls_id, conf in zip(boxes, track_ids, cls_ids, confs):
                if cls_id not in [2, 5, 7]: continue # Chỉ lấy Car, Bus, Truck
                
                curr_bottom = self.get_bottom_center(box)
                
                vehicle_info = {
                    "id": track_id,
                    "box": box,
                    "conf": conf,
                    "bottom": curr_bottom
                }
                valid_vehicles.append(vehicle_info)
                current_frame_ids.append(track_id)

                # Cập nhật danh sách để vẽ lên Web (Vẫn lưu để vẽ nhưng KHÔNG in log)
                self.latest_tracks.append({
                    "id": track_id, 
                    "box": box,
                    "bottom": curr_bottom
                })

            # 2. XỬ LÝ TRIGGER
            if valid_vehicles:
                # Tìm xe có độ tin cậy cao nhất
                best_vehicle = max(valid_vehicles, key=lambda x: x['conf'])
                
                tid = best_vehicle['id']
                curr_bottom = best_vehicle['bottom']
                curr_y = curr_bottom[1]

                # --- ĐÃ XÓA LOG LIÊN TỤC TẠI ĐÂY ---
                # (Dòng print trạng thái cũ đã bị xóa để tránh spam console)

                # Kiểm tra logic cắt vạch
                if tid in self.previous_bottoms:
                    prev_bottom = self.previous_bottoms[tid]
                    prev_y = prev_bottom[1]

                    # Logic: Nằm trong chiều ngang & Cắt từ trên xuống
                    if self.line_x_min <= curr_bottom[0] <= self.line_x_max:
                        if prev_y < self.line_y and curr_y >= self.line_y:
                            if tid not in self.triggered_ids:
                                # CHỈ IN KHI CÓ SỰ KIỆN QUAN TRỌNG
                                print(f">>> [TRIGGER] 🚀 XE ID {tid} (Conf {best_vehicle['conf']:.2f}) CẮT VẠCH")
                                self.triggered_ids[tid] = now
                                triggered_now = (True, tid)
            
            # 3. CẬP NHẬT LỊCH SỬ DI CHUYỂN
            for veh in valid_vehicles:
                self.previous_bottoms[veh['id']] = veh['bottom']

            # Dọn dẹp memory
            self.previous_bottoms = {k:v for k,v in self.previous_bottoms.items() if k in current_frame_ids}

        return triggered_now
