import cv2
import numpy as np
from ultralytics import YOLO

class CarDetector:
    def __init__(self, model_path='/home/huy/DK_AI/AI/weights/yolov8s.pt'):
        print(f"Loading Strict Car Detector: {model_path}...")
        self.model = YOLO(model_path)
        self.target_classes = [2, 5, 7]  # Car, Bus, Truck

        self.captured_ids = set()
        self.id_last_seen = {}
        self.frame_count = 0
        self.forget_threshold = 300 

        self.margin = 0.02
        self.zone_x_min = self.margin
        self.zone_x_max = 1 - self.margin
        self.zone_y_min = self.margin
        self.zone_y_max = 1 - self.margin

        self.min_area_ratio = 0.03
        self.max_occlusion_ratio = 0.05

        self.latest_box = None 
        self.latest_id = None

    def get_safe_zone(self, w, h):
        x1 = int(w * self.zone_x_min)
        x2 = int(w * self.zone_x_max)
        y1 = int(h * self.zone_y_min)
        y2 = int(h * self.zone_y_max)
        return (x1, y1, x2, y2)

    def is_cut_off(self, xywh, frame_w, frame_h):
        cx, cy, w, h = xywh
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2
        
        buffer = 15
        touch_left = x1 < buffer
        touch_top = y1 < buffer
        touch_right = x2 > (frame_w - buffer)
        touch_bottom = y2 > (frame_h - buffer)
        return touch_left or touch_top or touch_right or touch_bottom

    def is_full_box_in_zone(self, xywh, video_w, video_h):
        cx, cy, w, h = xywh
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2
        
        zone_x1 = video_w * self.zone_x_min
        zone_x2 = video_w * self.zone_x_max
        zone_y1 = video_h * self.zone_y_min
        zone_y2 = video_h * self.zone_y_max
        
        in_x = (x1 >= zone_x1) and (x2 <= zone_x2)
        in_y = (y1 >= zone_y1) and (y2 <= zone_y2)
        return in_x and in_y

    def smart_crop_75(self, frame, xywh):
        """Crop 75%"""
        img_h, img_w = frame.shape[:2]
        cx, cy, w, h = xywh
        
        target_ratio = 0.85
        new_w = w / target_ratio
        new_h = h / target_ratio
        
        x1 = int(cx - new_w / 2)
        y1 = int(cy - new_h / 2)
        x2 = int(cx + new_w / 2)
        y2 = int(cy + new_h / 2)
        
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(img_w, x2)
        y2 = min(img_h, y2)
        
        return frame[y1:y2, x1:x2]

    def calculate_occlusion(self, candidate_box, other_boxes):
        cx1, cy1, w1, h1 = candidate_box
        box1_area = w1 * h1
        b1_x1, b1_y1 = cx1 - w1/2, cy1 - h1/2
        b1_x2, b1_y2 = cx1 + w1/2, cy1 + h1/2

        for obs_box in other_boxes:
            cx2, cy2, w2, h2 = obs_box
            b2_x1, b2_y1 = cx2 - w2/2, cy2 - h2/2
            b2_x2, b2_y2 = cx2 + w2/2, cy2 + h2/2
            
            x_inter1 = max(b1_x1, b2_x1)
            y_inter1 = max(b1_y1, b2_y1)
            x_inter2 = min(b1_x2, b2_x2)
            y_inter2 = min(b1_y2, b2_y2)
            
            w_inter = max(0, x_inter2 - x_inter1)
            h_inter = max(0, y_inter2 - y_inter1)
            inter_area = w_inter * h_inter
            
            occlusion_ratio = inter_area / box1_area
            if occlusion_ratio > self.max_occlusion_ratio:
                return True 
        return False

    def detect(self, frame, capture_enabled=True):
        self.frame_count += 1
        video_h, video_w = frame.shape[:2]
        
        self.latest_box = None
        self.latest_id = None
        # self.raw_detections is now updated ATOMICALLY at the end

        # 1. TRACKING
        results = self.model.track(frame, persist=True, verbose=False, conf=0.25, tracker="bytetrack.yaml")
        
        if results[0].boxes.id is None:
            self.raw_detections = [] 
            return None, None

        boxes = results[0].boxes.xywh.cpu().numpy() 
        track_ids = results[0].boxes.id.int().cpu().tolist()
        cls_ids = results[0].boxes.cls.int().cpu().tolist()
        confs = results[0].boxes.conf.cpu().numpy()
        
        current_frame_vehicles = []
        _local_raw_detections = []

        # 2. ITERATING THROUGH VEHICLE AND ID
        for box, track_id, cls_id, conf in zip(boxes, track_ids, cls_ids, confs):
            if cls_id in self.target_classes:
       
                cx, cy, w, h = map(int, box)

                current_frame_vehicles.append({
                    'box': box,
                    'id': track_id,
                    'area': box[2] * box[3],
                    'conf': conf
                })
                # Store candidate for visualization
                _local_raw_detections.append((box, track_id, conf))
                
                self.id_last_seen[track_id] = self.frame_count
        
        # Fix Multiple Boxes: Keep ONLY the one with highest Confidence
        if _local_raw_detections:
            best_raw = max(_local_raw_detections, key=lambda x: x[2]) # Sort by Conf
            self.raw_detections = [(best_raw[0], best_raw[1])] # Update Atomic
        else:
            self.raw_detections = []


        # 3. FIND BEST CANDIDATE 
        best_vehicle = None
        max_area = 0
        
        sz_width = video_w * (self.zone_x_max - self.zone_x_min)
        sz_height = video_h * (self.zone_y_max - self.zone_y_min)
        safe_zone_area = sz_width * sz_height

        for veh in current_frame_vehicles:
            box = veh['box']
            track_id = veh['id']
            obj_area = veh['area']

            ratio = obj_area / safe_zone_area
            if ratio < self.min_area_ratio: 
                continue
            
            if self.is_cut_off(box, video_w, video_h): 
                continue

            other_boxes = [v['box'] for v in current_frame_vehicles if v['id'] != track_id]
            if self.calculate_occlusion(box, other_boxes): 
                continue

            if obj_area > max_area:
                max_area = obj_area
                best_vehicle = veh

        if self.frame_count % 30 == 0:
            ids_to_remove = [tid for tid in self.captured_ids 
                             if self.frame_count - self.id_last_seen.get(tid, 0) > self.forget_threshold]
            for tid in ids_to_remove:
                self.captured_ids.remove(tid)
                if tid in self.id_last_seen: del self.id_last_seen[tid]

        # 4. FINAL RESULT
        if best_vehicle and capture_enabled:
            bx, by, bw, bh = best_vehicle['box']
            x1, y1, x2, y2 = int(bx-bw/2), int(by-bh/2), int(bx+bw/2), int(by+bh/2)
            self.latest_box = (x1, y1, x2, y2)
            self.latest_id = best_vehicle['id']

            tid = best_vehicle['id']
            if tid not in self.captured_ids:
                if self.is_full_box_in_zone(best_vehicle['box'], video_w, video_h):
                    print(f">>> [DETECT] CAPTURE SUCCESS ID {tid}")
                    self.captured_ids.add(tid)
                    
                    # Crop ảnh và trả về
                    final_img = self.smart_crop_75(frame, best_vehicle['box'])
                    return final_img, tid
                
        return None, None
